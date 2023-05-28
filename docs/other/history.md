# History

This project existance was directly caused by lack of tool like that in the wild for postgres database. At the time (mid 2022) there were some bash scripts that could perform backup, but their overall quality was not very high. I moved one hobbyst (but production! with real clients) few GB database from managed cloud solution to my own VM and knew backups are necessary in the long run.

From there, after few iterations eventually I thought it would be also a good thing to backup some other projects in my k3s kubernetes cluster, and there are postgres, mysql and mariadb databases so decision to support all of them was natural.

Tried to wrote it in extensible way so new backup targets like databases and cloud providers can be added.