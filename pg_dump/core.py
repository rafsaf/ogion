import logging
import multiprocessing
import os
import pathlib
import re
import secrets
import subprocess
from datetime import datetime

import croniter

from pg_dump import config

log = logging.getLogger(__name__)


_MB_TO_BYTES = 1048576
_GB_TO_BYTES = 1073741824


class CoreSubprocessError(Exception):
    pass


def _get_human_folder_size_msg(folder_path: pathlib.Path):
    def get_folder_size_bytes(folder: str):
        total_size = os.path.getsize(folder)
        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
            if os.path.isfile(itempath):
                total_size += os.path.getsize(itempath)
            elif os.path.isdir(itempath):
                total_size += get_folder_size_bytes(itempath)
        return total_size

    folder_size = get_folder_size_bytes(str(folder_path))
    log.debug("get_folder_size_bytes size of %s: %s", folder_path, folder_size)

    if folder_size < _MB_TO_BYTES:
        size_msg = f"{folder_size} bytes ({round(folder_size / _MB_TO_BYTES, 3)} mb)"
    elif folder_size < _GB_TO_BYTES:
        size_msg = f"{round(folder_size / _MB_TO_BYTES, 3)} mb"
    else:
        size_msg = f"{round(folder_size / _GB_TO_BYTES, 3)} gb"
    return size_msg


def run_subprocess(shell_args: str) -> str:
    p = subprocess.Popen(
        shell_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True,
    )
    log.debug("run_subprocess running: '%s'", shell_args)
    output, err = p.communicate(timeout=config.SUBPROCESS_TIMEOUT_SECS)

    if p.returncode != 0:
        log.error("run_subprocess failed with status %s", p.returncode)
        log.error("run_subprocess stdout: %s", output)
        log.error("run_subprocess stderr: %s", err)
        raise CoreSubprocessError(
            f"run_subprocess '{shell_args}'\n"
            f"subprocess {p.pid} "
            f"failed with code: {p.returncode}"
        )
    else:
        log.debug("run_subprocess finished with status %s", p.returncode)
        log.debug("run_subprocess stdout: %s", output)
        log.debug("run_subprocess stderr: %s", err)
    return output


class PgDumpDatabase:
    def __init__(self, pg_dump: "PgDump", database) -> None:
        self.pg_dump = pg_dump
        self.db = database
        self.database_version: str = self.init_postgres_connection()
        self.backup_folder: pathlib.Path = self.init_backup_folder()
        self.next_backup = self.get_next_backup_time()

    def init_postgres_connection(self):
        log.debug(
            "init_postgres_connection start postgres connection to %s get pg version",
            self.db,
        )
        pg_version_regex = re.compile(r"PostgreSQL \d*\.\d* ")
        try:
            result = run_subprocess(
                f"psql -U {self.db.user} "
                f"-p {self.db.port} "
                f"-h {self.db.host} "
                f"{self.db.db} "
                f"-w --command 'SELECT version();'",
            )
        except CoreSubprocessError as err:
            log.error(err, exc_info=True)
            log.error(
                "init_postgres_connection unable to connect to database %s, exiting",
                self.db,
            )
            exit(1)

        version = None
        matches: list[str] = pg_version_regex.findall(result)

        for match in matches:
            version = match.strip().split(" ")[1]
            break
        if version is None:
            log.error(
                "init_postgres_connection error processing pg result from %s, db version is unknown: %s",
                self.db,
                result,
            )
            exit(1)
        log.debug(
            "init_postgres_connection calculated database %s version: %s",
            self.db,
            version,
        )
        return version

    def init_backup_folder(self):
        log.debug("init_backup_folder start %s", self.db)
        backup_folder_path = config.BACKUP_FOLDER_PATH / self.db.friendly_name
        log.debug(
            "init_backup_folder creating folder backup_folder_path %s",
            backup_folder_path,
        )
        backup_folder_path.mkdir(mode=0o740, parents=True, exist_ok=True)
        log.debug("init_backup_folder created %s", backup_folder_path)
        return backup_folder_path

    def get_next_backup_time(self) -> datetime:
        now = datetime.utcnow()
        cron = croniter.croniter(
            self.db.cron_rule,
            start_time=now,
        )
        next_backup = cron.get_next(ret_type=datetime)
        log.info("%s: next backup time %s.", self.db, next_backup)
        return next_backup

    def get_new_backup_full_path(self):
        log.debug("get_new_backup_full_path calculating new backup path")
        random_string = secrets.token_urlsafe(3)
        new_file = "{}_{}_{}_{}".format(
            datetime.utcnow().strftime("%Y%m%d_%H%M"),
            self.db.db,
            self.database_version,
            random_string,
        )
        new_folder = self.backup_folder / new_file
        log.debug(
            "get_new_backup_full_path calculated new backup folder: %s", new_folder
        )
        return new_folder

    def run_pg_dump(self, out: pathlib.Path):
        log.debug("run_pg_dump start")
        shell_args = (
            f"pg_dump -v -O -Fd -j {multiprocessing.cpu_count()} "
            f"-U {self.db.user} "
            f"-p {self.db.port} "
            f"-h {self.db.host} "
            f"{self.db.db} "
            f"-f {out}"
        )
        log.info("run_pg_dump start pg_dump in subprocess: %s", shell_args)
        run_subprocess(shell_args)
        log.debug(
            "run_pg_dump finished pg_dump, output folder: %s, size: %s",
            out,
            _get_human_folder_size_msg(out),
        )
        log.debug(
            "run_pg_dump start encryption of folder: %s",
            out,
        )
        gpg_out = pathlib.Path(f"{out}.gpg")
        gpg_out.mkdir(mode=0o740, parents=True, exist_ok=True)
        run_subprocess(f"mv {out / '*.gpg'} {gpg_out}")
        log.info(
            "run_pg_dump finished encryption, out folder: %s, size: %s",
            gpg_out,
            _get_human_folder_size_msg(gpg_out),
        )


class PgDump:
    def __init__(self) -> None:
        self.init_pgpass_file()

        self.pg_dump_databases: list[PgDumpDatabase] = []

    def init_pgpass_file(self):
        log.debug("init_pgpass_file start creating pgpass file")
        # for database in settings.PD_DATABASES:
        #     pgpass_text += "{}:{}:{}:{}:{}\n".format(
        #         database.host,
        #         database.port,
        #         database.user,
        #         database.db,
        #         database.password.get_secret_value(),
        #     )

        # log.debug("init_pgpass_file saving pgpass file")
        # with open(settings.PD_PGPASS_FILE_PATH, "w") as file:
        #     file.write(pgpass_text)

        log.debug("init_pgpass_file pgpass file saved")


# def encode(signer, payload, header=None, key_id=None):
#     """Make a signed JWT.

#     Args:
#         signer (google.auth.crypt.Signer): The signer used to sign the JWT.
#         payload (Mapping[str, str]): The JWT payload.
#         header (Mapping[str, str]): Additional JWT header payload.
#         key_id (str): The key id to add to the JWT header. If the
#             signer has a key id it will be used as the default. If this is
#             specified it will override the signer's key id.

#     Returns:
#         bytes: The encoded JWT.
#     """
#     if header is None:
#         header = {}

#     if key_id is None:
#         key_id = signer.key_id

#     header.update({"typ": "JWT"})

#     if "alg" not in header:
#         if es256 is not None and isinstance(signer, es256.ES256Signer):
#             header.update({"alg": "ES256"})
#         else:
#             header.update({"alg": "RS256"})

#     if key_id is not None:
#         header["kid"] = key_id

#     segments = [
#         _helpers.unpadded_urlsafe_b64encode(json.dumps(header).encode("utf-8")),
#         _helpers.unpadded_urlsafe_b64encode(json.dumps(payload).encode("utf-8")),
#     ]

#     signing_input = b".".join(segments)
#     signature = signer.sign(signing_input)
#     segments.append(_helpers.unpadded_urlsafe_b64encode(signature))

#     return b".".join(segments)


# import cryptography.exceptions
# from cryptography.hazmat import backends
# from cryptography.hazmat.primitives import hashes
# from cryptography.hazmat.primitives import serialization
# from cryptography.hazmat.primitives.asymmetric import padding


# def from_string(cls, key, key_id=None):

#     # return cls.from_string(
#     #     info[_JSON_FILE_PRIVATE_KEY], info.get(_JSON_FILE_PRIVATE_KEY_ID)
#     # )
#     """Construct a RSASigner from a private key in PEM format.

#     Args:
#         key (Union[bytes, str]): Private key in PEM format.
#         key_id (str): An optional key id used to identify the private key.

#     Returns:
#         google.auth.crypt._cryptography_rsa.RSASigner: The
#         constructed signer.

#     Raises:
#         ValueError: If ``key`` is not ``bytes`` or ``str`` (unicode).
#         UnicodeDecodeError: If ``key`` is ``bytes`` but cannot be decoded
#             into a UTF-8 ``str``.
#         ValueError: If ``cryptography`` "Could not deserialize key data."
#     """
#     key = _helpers.to_bytes(key)
#     private_key = serialization.load_pem_private_key(
#         key, password=None, backend=_BACKEND
#     )
#     return cls(private_key, key_id=key_id)


# def _make_authorization_grant_assertion(self):
#     """Create the OAuth 2.0 assertion.

#     This assertion is used during the OAuth 2.0 grant to acquire an
#     access token.

#     Returns:
#         bytes: The authorization grant assertion.
#     """
#     now = _helpers.utcnow()
#     lifetime = datetime.timedelta(seconds=_DEFAULT_TOKEN_LIFETIME_SECS)
#     expiry = now + lifetime

#     payload = {
#         "iat": _helpers.datetime_to_secs(now),
#         "exp": _helpers.datetime_to_secs(expiry),
#         # The issuer must be the service account email.
#         "iss": self._service_account_email,
#         # The audience must be the auth token endpoint's URI
#         "aud": _GOOGLE_OAUTH2_TOKEN_ENDPOINT,
#         "scope": _helpers.scopes_to_string(self._scopes or ()),
#     }

#     payload.update(self._additional_claims)

#     # The subject can be a user email for domain-wide delegation.
#     if self._subject:
#         payload.setdefault("sub", self._subject)

#     token = jwt.encode(self._signer, payload)

#     return token
