import pwd
import os
import sys
import subprocess

# Defines the service that runs the intercom.
SERVICE_DEFINITION = """
[Unit]
Description = RPi Mumble Intercom Client
Requires = systemd-user-sessions.service network.target sound.target
After = multi-user.target

[Service]
User = rpi-intercom
Group = rpi-intercom
Type = simple
ExecStart = python -u -m rpi_intercom --config {config_path}
Restart = always
RestartSec = 5

[Install]
WantedBy = multi-user.target
"""

ASOUND_CONFIGURATION = """
defaults.pcm.card {index}
defaults.ctl.card {index}
"""

class FailedInstall(Exception):
    """Error thrown when the installation fails for a known reason"""
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class InstallService:
    """
    Installs the intercom as a python service that runs in the background.
    This is designed to work on a raspberry pi or other debian based system.
    It will probbaly fail on others.
    """
    def __init__(self):
        pass

    def run(self):
        try:
            self._run()
        except FailedInstall as e:
            print(e.message)

    def _run(self):
        print(__file__)
        if len(sys.argv) < 3 or not os.path.exists(sys.argv[2]):
            raise FailedInstall("Please specify a valid path to a file to use for the intercom's configuration.  Example:\n    sudo python -m rpi_intercom /path/to/a/configuration/file.yaml")
        if os.getuid() != 0:
            raise FailedInstall("Please run this script with sudo.  Example:\n    sudo python -m rpi_intercom /path/to/a/configuration/file.yaml")

        print("This script will:")
        print(" - Create a user named 'rpi-intercom' with limited permissions to run the intercom service")
        print(" - Install the rpi-intercom service")
        print(" - Configure the service to start at boot")
        print("Do you want to continue [yes/no]?")
        response = input()
        if not response.lower().startswith("y"):
            print("OK!")
            raise FailedInstall("Install cancelled by user")
        print()
        user_created = False
        for user in pwd.getpwall():
            if user.pw_name == "rpi-intercom":
                user_created = True
        if not user_created:
            print("Creating 'rpi-intercom' user")
            self._run_process(['adduser', '--disabled-password', '--disabled-login', '--gecos', "rpi-intercom service user", 'rpi-intercom'])
            self._run_process(['usermod', '-a', '-G', 'cdrom,audio,video,plugdev,users,dialout,dip,input,gpio', 'rpi-intercom'])
        else:
            print("rpi-intercom user already exists, setting up user permissions")
            self._run_process(['usermod', '-a', '-G', 'cdrom,audio,video,plugdev,users,dialout,dip,input,gpio', 'rpi-intercom'])
        
        config_path = os.path.abspath(sys.argv[2])
        self._run_process(['chgrp', 'rpi-intercom', config_path])

        print("Creating service configuration file")
        service_source_file_path = os.path.abspath(os.path.join(__file__, "..", "data", "rpi-intercom.service"))
        service_dest_file_path = "/etc/systemd/system/rpi-intercom.service"
        with open(service_dest_file_path, "w") as dest:
            dest.write(SERVICE_DEFINITION.replace("{config_path}", config_path))

        print("Enabling the service")
        self._run_process(['systemctl', 'enable', 'rpi-intercom.service'])

        print("Restarting the service daemon")
        self._run_process(['systemctl', 'daemon-reload'])

        print("Restarting the service")
        self._run_process(['service', 'rpi-intercom', 'restart'])

        print("The rpi-intercom client is now installaed as a service and will automatically start on boot.  You can view the service status and logs by running:")
        print("  service rpi-intercom status")
        print("You can start or stop the service by running:")
        print("  service rpi-intercom stop")
        print("  service rpi-intercom start")
        print("  service rpi-intercom restart")

    def _run_process(self, args) -> subprocess.CompletedProcess[str]:
        info = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if info.returncode != 0:
            message = f"Command: \"{' '.join(args)}\" returned status code {info.returncode}.  Here is the output in case that helps:\n"
            message += "stdout:\n"
            message += info.stdout.decode("utf-8") + "\n"
            message += "stderr:\n"
            message += info.stderr.decode("utf-8")
            raise FailedInstall(message)
        return info