#!/bin/bash

destroy () {
  ansible-playbook -i ../hosts destroy-infra.yml -v
}

echo "THIS SCRIPT DESTROYS THE ENTIRE WEBSITE INCLUDING DATABASE AND STORAGE!"
read -p "Are you sure you wish to continue? (y/n)?" choice
case "$choice" in
  y|Y ) destroy;;
  n|N ) echo "Doing nothing. Exiting.";;
  * ) echo "Invalid choice. Exiting.";;
esac
