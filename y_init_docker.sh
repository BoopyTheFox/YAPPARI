#!/bin/bash

container_name="tg_yappari"

display_help() {
  echo "Usage: $0 <BOT_OWNER> <BOT_TOKEN> <OPENAI_API_KEY>" 
  exit 0
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
  display_help
fi

if ! docker ps > /dev/null 2>&1; then
  echo "Insufficient privileges to run Docker. Please add your user to the docker group or run as root."
  exit 1
fi

if [ "$(docker ps -a | grep tg_yappari)" ]; then
  echo "$container_name container already exists. Exiting."
  exit 1
fi

if [ "$#" -ne 3 ]; then
  display_help
  exit 1
fi

BOT_OWNER=$1
BOT_TOKEN=$2
OPENAI_API_KEY=$3

cat <<EOF > ./app/y_secrets.env
BOT_OWNER=$BOT_OWNER
BOT_TOKEN=$BOT_TOKEN
OPENAI_API_KEY=$OPENAI_API_KEY
EOF

echo "THIS IS ./app/y_sercrets.env"
cat ./app/y_secrets.env

docker build -t $container_name . && docker run -d --name $container_name $container_name

if [ $? -eq 0 ]; then
  echo "$container_name container is now running."
else
  echo "Failed to start $container_name container."
fi

rm ./app/y_secrets.env
