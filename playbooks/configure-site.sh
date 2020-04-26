#!/bin/bash

ansible-playbook create-infra.yml
echo "Waiting for infrastructure to be accessible..."
sleep 30
ansible-playbook -i ../hosts configure-infra.yml
