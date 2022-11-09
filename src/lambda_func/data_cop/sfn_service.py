"""
Module for executing sfn step functions and
what not.
"""
import json

from data_cop.logging_config import LoggerConfig
from data_cop.enums_ import DataCopEnum


class SfnService:
    """
    This class is responsible for interacting with
    SFN APIs.
    """

    DC_FSS_SFN_NAME = "DCFssStepFunction"
    DC_MACIE_SFN_NAME = "DCMacieStepFunction"

    def __init__(self, boto_session):
        self.sfn_client = boto_session.client("stepfunctions")
        self.logger = LoggerConfig().configure(type(self).__name__)

    def execute_sfn(self, event, _type):
        """
        Execute the step function and pass in the event
        """
        state_machine_arn = self.find_state_machine(_type)

        response = self.sfn_client.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps(event),
        )
        self.logger.info(
            "Executed the state machine for FSS: %s", response["executionArn"]
        )

    def find_state_machine(self, _type):
        """
        Find the state machine based on the type
        of event.
        """
        state_machine_arn = None
        sfn_response = self.sfn_client.list_state_machines()
        for state_machine in sfn_response["stateMachines"]:
            state_machine_name = state_machine["name"]
            if _type == DataCopEnum.FSS:
                if self.DC_FSS_SFN_NAME in state_machine_name:
                    state_machine_arn = state_machine["stateMachineArn"]
                    break
        return state_machine_arn
