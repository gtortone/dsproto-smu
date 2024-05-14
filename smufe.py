#!/usr/bin/env python3

import sys
import midas
import midas.frontend
import midas.event
from pyvisa import ResourceManager

from smudriver import SMUModel, SMUDevice, SMUFactory

class SMU(midas.frontend.EquipmentBase):

    def __init__(self, client, session, model):

        self.session = session
        self.smu = SMUFactory(model, session)

        equip_name = f'SMU-{model}-{str(midas.frontend.frontend_index).zfill(2)}'

        default_common = midas.frontend.InitialEquipmentCommon()
        default_common.equip_type = midas.EQ_PERIODIC
        default_common.buffer_name = "SYSTEM"
        default_common.trigger_mask = 0
        default_common.event_id = 80
        default_common.period_ms = 5000   # event data frequency update (in milliseconds)
        default_common.read_when = midas.RO_ALWAYS
        default_common.log_history = 1

        midas.frontend.EquipmentBase.__init__(self, client, equip_name, default_common, self.smu.getSettingsSchema());

        self.odb_readback_dir = f"/Equipment/{equip_name}/Readback"

        self.updateODB()

    def debug(self):
        print(f'source func: {self.smu.getSource()}')
        print(f'source level: {self.smu.getSourceLevel()}')
        print(f'Vsource range: {self.smu.getSourceVoltageRange()}')
        print(f'Isource range: {self.smu.getSourceCurrentRange()}')
        print("*")

    def readout_func(self):
        self.debug()
        self.updateODB()

    def detailed_settings_changed_func(self, path, idx, new_value):
        if path == f'{self.odb_settings_dir}/source Vrange':
            self.smu.setSourceVoltageRange(new_value)
        elif path == f'{self.odb_settings_dir}/source Irange':
            self.smu.setSourceCurrentRange(new_value)
        elif path == f'{self.odb_settings_dir}/source':
            self.smu.setSource(new_value)
        elif path == f'{self.odb_settings_dir}/source level':
            self.smu.setSourceLevel(new_value)

        # handle errors...

    def updateODB(self):
        readback = self.smu.getReadbackSchema()
        settings = self.smu.getSettingsSchema()

        readback['source Vrange'] = self.smu.getSourceVoltageRange()[0]
        readback['source Irange'] = self.smu.getSourceCurrentRange()[0]

        self.client.odb_set(self.odb_readback_dir, readback, remove_unspecified_keys=False)

        settings['source'] = self.smu.getSource()
        settings['source level'] = self.smu.getSourceLevel()
        settings['source Vrange'] = self.smu.getSourceVoltageRange()[1]
        settings['source Irange'] = self.smu.getSourceCurrentRange()[1]

        if(settings != self.settings):
            for k,v in settings.items():
                if settings[k] != self.settings[k]:
                    self.client.odb_set(f'{self.odb_settings_dir}/{k}', v, remove_unspecified_keys=False)

class SMUFrontend(midas.frontend.FrontendBase):

    def __init__(self, session, model):
        if(midas.frontend.frontend_index == -1):
            print("E: set frontend index with -i option")
            sys.exit(-1)
        midas.frontend.FrontendBase.__init__(self, f"SMU-{model}")
        self.add_equipment(SMU(self.client, session, model))

if __name__ == "__main__":
    parser = midas.frontend.parser
    parser.add_argument("--ip", required=True)
    parser.add_argument("--model", required=True, choices = [m.value[0] for m in SMUModel])
    args = midas.frontend.parse_args()

    # lookup for SMU
    rm = ResourceManager()
    dev = f'TCPIP0::{args.ip}::5025::SOCKET'
    session = rm.open_resource(dev)
    session.read_termination = '\n'
    session.write_termination = '\n'

    try:
        model = session.query('*IDN?').split(',')[1]
    except Exception as e:
        print(f"E: {e}")
        sys.exit(-1)

    print(model)

    if model.startswith("MODEL "):
        model = model.split(' ')[1]

    if model == args.model:
        print(f"I: SMU {model} found on {args.ip}")
    else:
        print(f"E: SMU {args.model} not found on {args.ip}")
        sys.exit(-1)

    equip_name = f'SMU-{model}-{str(midas.frontend.frontend_index).zfill(2)}'

    # check if a SMU frontend is running with same model and id
    with midas.client.MidasClient("smu") as c:

        if c.odb_exists(f"/Equipment/{equip_name}/Common/Frontend name"):
            fename = c.odb_get(f"/Equipment/{equip_name}/Common/Frontend name")

            if c.odb_get(f"/Equipment/{equip_name}"):
                for cid in c.odb_get(f'/System/Clients'):
                    if c.odb_get(f'/System/Clients/{cid}/Name') == fename:
                        c.msg(f"{equip_name} already running on MIDAS server, please change frontend index")
                        sys.exit(-1)

    fe = SMUFrontend(session, model)
    fe.run()
