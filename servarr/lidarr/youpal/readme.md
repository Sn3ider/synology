# YouPAL - Youtube Playlist Artist Lister

It will give you a simple WebUI to add the YouTube playlist and provide an API where it will list the MusicBrainz information.

The goal is to create an app that would provide a custom list for Lidarr to tap into.

This is a WORK IN PROGMESS project, came up with the idea and created a quick solution for it under a lunch break.
The solution is 100%, still in development mode and can have some flaws as I haven't done any testing nor properly package it.


**PORT**: 8687

**API**: http://YOUR_IP_ADDRESS:8687/api/artists




# Docker Compose:
```
version: '3.8'

services:
  youpal-app:
    image: sn3ider/youpal:latest
    container_name: youpal
    ports:
      - "8688:8687"
    volumes:
      - ./app/db:/app/db
    restart: unless-stopped
    networks:
      servarr:
          ipv4_address: 172.20.0.20

networks:
  servarr:
    name: servarr
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.20.0.0/16
          ip_range: 172.20.0.0/16
          gateway: 172.20.0.1
```

If you are using this docker compose then pay attention to the port you are using.
