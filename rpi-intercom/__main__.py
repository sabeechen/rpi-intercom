from encodings import utf_8
import pwd
import os
import sys
import subprocess


def install_service():
    print(__file__)
    if len(sys.argv) < 3 or not os.path.exists(sys.argv[2]):
        print("Please specify a valid path to a file to use for the intercom's configuration.  Example:")
        print("sudo python -m rpi-intercom /path/to/a/configuration/file.yaml")
        return
    if os.getuid() != 0:
        print("Please run this script with sudo.  Example:")
        print("sudo python -m rpi-intercom /path/to/a/configuration/file.yaml")
        return

    print("This script will:")
    print(" - Create a user named 'rpi-intercom' with limited permissions to run the intercom service")
    print(" - Apt-get dependencies needed for the intercom service")
    print(" - Install the intercom service")
    print(" - Configure the intercom service to start at boot")
    print("Do you want to continue [yes/no]?")
    response = input()
    if not response.lower().startswith("y"):
        print("OK!")
        return

    print("Installing python3-audio")
    run_process(['apt-get', 'install', '-y', 'python3-pyaudio'])
    
    user_created = False
    for user in pwd.getpwall():
        if user.pw_name == "rpi-intercom":
            user_created = True
    if not user_created:
        print("Creating 'rpi-intercom' user")
        run_process(['adduser', '--disabled-password', '--disabled-login', '--gecos', "rpi-intercom service user", 'rpi-intercom'])
        run_process(['usermod', '-a', '-G', 'cdrom,audio,video,plugdev,users,dialout,dip,input,gpio', 'rpi-intercom'])
    else:
        print("rpi-intercom user already exists, setting up user permissions")
        run_process(['usermod', '-a', '-G', 'cdrom,audio,video,plugdev,users,dialout,dip,input,gpio', 'rpi-intercom'])
    
    config_path = os.path.abspath(sys.argv[2])
    run_process(['chgrp', 'rpi-intercom', config_path])

    print("Creating service configuration file")
    service_source_file_path = os.path.abspath(os.path.join(__file__, "..", "data", "rpi-intercom.service"))
    service_dest_file_path = "/etc/systemd/system/rpi-intercom.service"
    with open(service_dest_file_path, "w") as dest:
        with open(service_source_file_path, "r") as src:
            for line in src.readlines():
                dest.write(line.replace("{config_path}", config_path))

    print("Enabling the service")
    run_process(['systemctl', 'enable', 'rpi-intercom.service'])

    print("Restarting the service daemon")
    run_process(['systemctl', 'daemon-reload'])

    print("Restarting the service")
    run_process(['service', 'rpi-intercom', 'restart'])

    print("The intercom client is now installaed as a service and will automatically start on boot.  You can view the service status and logs by running:")
    print("  service rpi-intercom status")
    print("You can start or stop the service by running:")
    print("  service rpi-intercom stop")
    print("  service rpi-intercom start")
    print("  service rpi-intercom restart")

def run_process(args):
    info = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if info.returncode != 0:
        print(f"Command: \"{' '.join(args)}\" returned status code {info.returncode}.  Here is the output in case that helps:")
        print("stdout:")
        print(info.stdout.decode("utf-8"))
        print("stderr:")
        print(info.stderr.decode("utf-8"))

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "install-service":
        install_service()
    else:
        from .intercom import Intercom
        from .config import Config
        Intercom(Config.fromArgs()).run()
