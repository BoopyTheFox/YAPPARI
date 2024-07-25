#!/bin/bash

APP_NAME="tg_yappari"
APP_DIR="/opt/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
SECRETS_FILE="$APP_DIR/y_secrets.env"
VENV_DIR="$APP_DIR/venv"
REQUIREMENTS_FILE="$APP_DIR/requirements.txt"

## Helpers

display_help() {
  echo "Usage: $0 <BOT_OWNER> <BOT_TOKEN> <OPENAI_API_KEY>"
  echo "or"
  echo "$0 --uninstall"
  exit 0
}

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)."
  exit 1
fi

if [[ $1 == "-h" || $1 == "--help" ]]; then
  display_help
fi

## Uninstaller

if [ "$#" -eq 1 ] && [[ $1 == "--uninstall" ]]; then
  if systemctl is-active --quiet $APP_NAME; then
    echo "Stopping $APP_NAME service..."
    systemctl stop $APP_NAME
  fi

  if systemctl is-enabled --quiet $APP_NAME; then
    echo "Disabling $APP_NAME service..."
    systemctl disable $APP_NAME
  fi

  echo "Removing $APP_NAME service..."
  systemctl disable $APP_NAME
  rm -f $SERVICE_FILE

  echo "Removing application directory..."
  rm -rf $APP_DIR

  echo "$APP_NAME has been uninstalled."
  exit 0
fi

if [ "$#" -ne 3 ]; then
  display_help
  exit 1
fi

## Set secrets

BOT_OWNER=$1
BOT_TOKEN=$2
OPENAI_API_KEY=$3

mkdir -p $APP_DIR
cp app/* $APP_DIR

cat <<EOF > $SECRETS_FILE
BOT_OWNER=$BOT_OWNER
BOT_TOKEN=$BOT_TOKEN
OPENAI_API_KEY=$OPENAI_API_KEY
EOF

# Create virtual environment and install dependencies

python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate
pip install -r $REQUIREMENTS_FILE
deactivate

# Create systemd service

cat <<EOF > $SERVICE_FILE
[Unit]
Description=$APP_NAME service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$APP_DIR
EnvironmentFile=$SECRETS_FILE
ExecStart=$VENV_DIR/bin/python $APP_DIR/y_bot.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Launch it

systemctl daemon-reload

systemctl start $APP_NAME

if systemctl is-active --quiet $APP_NAME; then
  echo "$APP_NAME service is now running."
else
  echo "Failed to start $APP_NAME service."
  exit 1
fi

## Notify

echo "$APP_NAME has been successfully set up."
echo "--- To start on boot:" 
echo "sudo systemctl enable $APP_NAME"

