'''
This is a standalone script that will check to see if Macie is configured or not.
This is supposed to be executed prior to deployment.
'''
import time

from data_cop.session_config import BotoConfig
from data_cop.logging_config import LoggerConfig

class MacieSetup:

    def __init__(self):
        self.logger = LoggerConfig().configure(__name__)
        self.macie_client = BotoConfig().get_session().client("macie2")

    def enable_macie(self):
        enabled = self.check_macie_status()
        if not enabled:
            self.logger.info("Macie is not enabled. Enabling now...")
            self.macie_client.enable_macie(
                status='ENABLED'
            )
            time.sleep(10) # Wait 10 seconds

            # Checking to see if it's enabled
            enabled = self.check_macie_status()
            if not enabled:
                raise Exception("Macie is not enabled. Please enable it manually before continuing with deployment.")

    def check_macie_status(self):
        is_enabled = True

        try:
            self.macie_client.get_macie_session()
        except self.macie_client.exceptions.AccessDeniedException:
            is_enabled = False

        return is_enabled

    def disable_macie(self):
        self.macie_client.disable_macie()
        self.logger.info("Macie has been disabled for this account.")

def main():
    macie_setup = MacieSetup()
    macie_setup.enable_macie()

if __name__ == '__main__':
    main()