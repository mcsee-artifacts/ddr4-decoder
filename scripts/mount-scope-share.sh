#!/usr/bin/env bash

function umt () {
   MNT_PT="$1"
   echo "[>] unmounting ${MNT_PT}..."
   sudo umount -f ${MNT_PT} &>/dev/null
   sudo rmdir ${MNT_PT}
}

function mt () {
   MNT_PT="$1"
   echo "[>] mounting ${MNT_PT}..."
   sudo useradd -s /sbin/nologin LeCroyUser &>/dev/null
   sudo apt-get install -y cifs-utils 1>/dev/null
   sudo mkdir -p ${MNT_PT}
   sudo mount -t cifs -o user=LeCroyUser,password=lecroyservice,defaults,noperm //172.31.200.250/$2 ${MNT_PT}
   sudo chown pjattke:"domain users" ${MNT_PT}
}


umt /mnt/scope-data &>/dev/null
mt /mnt/scope-data scope-data 1>/dev/null

umt /mnt/scope-data-archive &>/dev/null
mt /mnt/scope-data-archive scope-data-archive 1>/dev/null
