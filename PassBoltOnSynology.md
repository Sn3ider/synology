# How to install PastBolt on Synology NAS?

# Install MariaDB

# Setup MariaDB
```bash
ssh username@YOUR.NAS.IP.ADDRESS
```
```bash
mysql -u root -p
```
```bash
use mysql;
```
```bash
CREATE USER 'passbolt'@'172.17.0.%' IDENTIFIED BY 'password';
```
```bash
create database passbolt;
```
```bash
use passbolt;
```
```bash
grant all privileges on 'passbolt' to 'passbolt'@'172.17.0.%';
```
```bash
FLUSH PRIVILEGES;
```




# Install Docker

# Install PastBolt
HealthCheck:
```bash
su -s /bin/bash -c "./bin/cake passbolt healthcheck" www-data
```

Register Admin:
```bash
su -s /bin/bash -c "/usr/share/php/passbolt/bin/cake passbolt register_user -u YOUREMAIL -f YOURFIRSTNAME -l YOURLASTNAME -r admin" www-data
```