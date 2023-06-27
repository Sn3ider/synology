# How to install PastBolt on Synology NAS?
# Setup Reverse Proxy

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

# Setup SMTP Google account
Generate App Password:

[AppPasswordURL](https://myaccount.google.com/apppasswords)

# Install PassBolt
VARIABLES
```bash
APP_FULL_BASE_URL = https://passbolt.dlnasmain.synology.me
DATASOURCES_DEFAULT_HOST = 172.17.0.1
DATASOURCES_DEFAULT_USERNAME = passbolt
DATASOURCES_DEFAULT_PASSWORD = YOUR_DB_PASSWORD
DATASOURCES_DEFAULT_DATABASE = passbolt
DATASOURCES_DEFAULT_PORT = YOUR_DEFAULT_DB_PORT
PASSBOLT_REGISTRATION_PUBLIC = true
PASSBOLT_SECURITY_SMTP_SETTINGS_ENDPOINTS_DISABLED = true
PASSBOLT_KEY_NAME = YOUR_USER_NAME
PASSBOLT_KEY_EMAIL = YOUR_EMAIL
EMAIL_DEFAULT_FROM = SMTP_GMAIL_ADDRESS
EMAIL_TRANSPORT_DEFAULT_HOST = smtp.gmail.com
EMAIL_TRANSPORT_DEFAULT_PORT = 587
EMAIL_TRANSPORT_DEFAULT_USERNAME = SMTP_GMAIL_ADDRESS
EMAIL_TRANSPORT_DEFAULT_PASSWORD = APP_PASSWORD
EMAIL_TRANSPORT_DEFAULT_TLS = true
TZ = GMT
```

Mount:
```bash
/etc/passbolt/gpg
/etc/passbolt/jwt
/etc/ssl/certs/
```

HealthCheck:
```bash
su -s /bin/bash -c "./bin/cake passbolt healthcheck" www-data
```

Register Admin:
```bash
su -s /bin/bash -c "/usr/share/php/passbolt/bin/cake passbolt register_user -u YOUREMAIL -f YOURFIRSTNAME -l YOURLASTNAME -r admin" www-data
```
