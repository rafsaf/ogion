import logging
import re
import secrets
import subprocess
from datetime import datetime

from pg_dump import config

log = logging.getLogger(__name__)


_MB_TO_BYTES = 1048576
_GB_TO_BYTES = 1073741824


class CoreSubprocessError(Exception):
    pass


def run_subprocess(shell_args: str) -> str:
    log.debug("run_subprocess running: '%s'", shell_args)
    p = subprocess.run(
        shell_args,
        capture_output=True,
        text=True,
        shell=True,
        timeout=config.SUBPROCESS_TIMEOUT_SECS,
    )
    if p.returncode:
        log.error("run_subprocess failed with status %s", p.returncode)
        log.error("run_subprocess stdout: %s", p.stdout)
        log.error("run_subprocess stderr: %s", p.stderr)
        raise CoreSubprocessError()

    log.debug("run_subprocess finished with status %s", p.returncode)
    log.debug("run_subprocess stdout: %s", p.stdout)
    log.debug("run_subprocess stderr: %s", p.stderr)
    return p.stdout


def get_new_backup_path(db_version: str):
    random_string = secrets.token_urlsafe(3)
    new_file = "{}_{}_{}_{}".format(
        datetime.utcnow().strftime("%Y%m%d_%H%M"),
        config.POSTGRES_DB,
        db_version,
        random_string,
    )
    return new_file


def run_pg_dump(db_version: str):
    out_file = get_new_backup_path(db_version)

    shell_args = (
        f"pg_dump -v -O -Fc "
        f"-U {config.POSTGRES_USER} "
        f"-p {config.POSTGRES_PORT} "
        f"-h {config.POSTGRES_HOST} "
        f"{config.POSTGRES_DB} "
        f"-f {out_file}"
    )
    log.debug("run_pg_dump start pg_dump in subprocess: %s", shell_args)
    run_subprocess(shell_args)
    log.debug("run_pg_dump finished pg_dump, output: %s", out_file)
    return out_file


def postgres_connection():
    log.debug("postgres_connection start postgres connection")
    pg_version_regex = re.compile(r"PostgreSQL \d*\.\d* ")
    try:
        result = run_subprocess(
            f"psql -U {config.POSTGRES_USER} "
            f"-p {config.POSTGRES_PORT} "
            f"-h {config.POSTGRES_HOST} "
            f"{config.POSTGRES_DB} "
            f"-w --command 'SELECT version();'",
        )
    except CoreSubprocessError as err:
        log.error(err, exc_info=True)
        log.error("postgres_connection unable to connect to database, exiting")
        exit(1)

    version = None
    matches: list[str] = pg_version_regex.findall(result)

    for match in matches:
        version = match.strip().split(" ")[1]
        break
    if version is None:
        log.error(
            "postgres_connection error processing pg result, version unknown: %s",
            result,
        )
        exit(1)
    log.debug("postgres_connection calculated version: %s", version)
    return version


def init_pgpass_file():
    pgpass_text = "{}:{}:{}:{}:{}".format(
        config.POSTGRES_HOST,
        config.POSTGRES_PORT,
        config.POSTGRES_USER,
        config.POSTGRES_DB,
        config.POSTGRES_PASSWORD,
    )
    with open(config.PGPASS_FILE_PATH, "w") as file:
        file.write(pgpass_text)


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
