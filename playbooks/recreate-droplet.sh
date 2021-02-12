#!/bin/bash

recreate_droplet () {
  echo "Destroying droplet..."
  ansible-playbook destroy-droplet.yml -v
  sleep 30

  echo "Recreating droplet..."
  ansible-playbook create-infra.yml -v
  echo "Waiting for infrastructure to be available..."
  sleep 30

  echo "Reconfiguring droplet."
  ansible-playbook -i ../hosts configure-infra.yml -v
  echo "NOTE: You will need to reconfigure SSL as initial certbot configuration is not automated."
}

echo "THIS SCRIPT WILL DESTROY AND RECREATE YOUR DROPLET!"
read -p "Are you sure you wish to continue? (y/n)?" choice
case "$choice" in
  y|Y ) recreate_droplet;;
  n|N ) echo "Doing nothing. Exiting.";;
  * ) echo "Invalid choice. Exiting.";;
esac
