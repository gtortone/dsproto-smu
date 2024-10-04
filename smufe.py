#!/usr/bin/env python3

import sys
import midas
import midas.frontend
import midas.event
from pyvisa import ResourceManager

from smudriver import SMUModel, SMUDevice, SMUFactory
from utils import flatten_dict

class SMU(midas.frontend.EquipmentBase):

    def __init__(self, client, model):

        default_common = midas.frontend.InitialEquipmentCommon()
        default_common.equip_type = midas.EQ_PERIODIC
        default_common.buffer_name = "SYSTEM"
        default_common.trigger_mask = 0
        default_common.event_id = 80
        default_common.period_ms = 5000   # event data frequency update (in milliseconds)
        default_common.read_when = midas.RO_ALWAYS
        default_common.log_history = 1

        equip_name = f'SMU-{model}-{str(midas.frontend.frontend_index).zfill(2)}'
        self.smu = SMUFactory(model)

        midas.frontend.EquipmentBase.__init__(self, client, equip_name, default_common, self.smu.getSettingsSchema());

        ipaddress = self.settings['ip address']
        if ipaddress == "":
            self.client.msg(f"please set IP address to /Equipment/{equip_name}/Settings/ip address", is_error=True)
            self.client.communicate(1000)
            sys.exit(-1)

        # lookup for SMU
        rm = ResourceManager()
        dev = f'TCPIP0::{ipaddress}::5025::SOCKET'

        self.session = None
        try:
            self.session = rm.open_resource(dev)
        except Exception as e:
            self.client.communicate(1000)
            self.client.msg(f"{e}", is_error=True)
            sys.exit(-1)

        self.session.read_termination = '\n'
        self.session.write_termination = '\n'

        readmodel = None
        try:
            readmodel = self.session.query('*CLS; *IDN?').split(',')[1]
        except Exception as e:
            self.client.msg(f"No device found on {ipaddress}", is_error=True)
            self.client.communicate(1000)
            sys.exit(-1)

        if readmodel.startswith("MODEL "):
            readmodel = readmodel.split(' ')[1]

        if model == readmodel:
            self.client.msg(f"SMU {model} found on {ipaddress}")
        else:
            self.client.msg(f"SMU {model} not found on {ipaddress}", is_error=True)
            self.client.communicate(1000)
            sys.exit(-1)

        self.smu.setSession(self.session)
        self.smu.reset()

        self.odb_readback_dir = f"/Equipment/{equip_name}/Readback"

        self.updateODB()

    def debug(self):
        print(f'output: {self.smu.getOutput()}')
        print(f'terminals: {self.smu.getTerminals()}')
        print("-")
        print(f'source func: {self.smu.getSource()}')
        print(f'source level: {self.smu.getSourceLevel()}')
        print(f'source Vrange: {self.smu.getRange("SOURCE", "VOLT")}')
        print(f'source Irange: {self.smu.getRange("SOURCE", "CURR")}')
        print(f'source Vlimit: {self.smu.getLimit("VOLT")}')
        print(f'source Ilimit: {self.smu.getLimit("CURR")}')
        print("-")
        print(f'voltage: {self.smu.getVoltage()}')
        print(f'current: {self.smu.getCurrent()}')
        print(f'measure Vrange: {self.smu.getRange("SENS", "VOLT")}')
        print(f'measure Irange: {self.smu.getRange("SENS", "CURR")}')
        print("-")
        print(self.smu.getLastError())
        print("***")

    def readout_func(self):
        #self.debug()
        self.updateODB()
        event = midas.event.Event()

        event.create_bank('SVAL', midas.TID_FLOAT, [float(self.smu.getSourceLevel())])
        event.create_bank('VOLT', midas.TID_FLOAT, [float(self.smu.getVoltage())])
        event.create_bank('CURR', midas.TID_FLOAT, [float(self.smu.getCurrent())])
        event.create_bank('OUTP', midas.TID_INT32, [int(self.smu.getOutput())])

        return event

    def detailed_settings_changed_func(self, path, idx, new_value):
        if path == f'{self.odb_settings_dir}/output':
            self.smu.setOutput(new_value)
        elif path == f'{self.odb_settings_dir}/source/function':
            self.smu.setSource(new_value)
        elif path == f'{self.odb_settings_dir}/source/level':
            self.smu.setSourceLevel(new_value)
        elif path == f'{self.odb_settings_dir}/source/Vrange':
            self.smu.setRange("SOURCE", "VOLT", new_value)
        elif path == f'{self.odb_settings_dir}/source/Irange':
            self.smu.setRange("SOURCE", "CURR", new_value)
        elif path == f'{self.odb_settings_dir}/measure/Vrange':
            self.smu.setRange("SENS", "VOLT", new_value)
        elif path == f'{self.odb_settings_dir}/measure/Irange':
            self.smu.setRange("SENS", "CURR", new_value)
        elif path == f'{self.odb_settings_dir}/terminals':
            self.smu.setTerminals(new_value)
        elif path == f'{self.odb_settings_dir}/source/Vlimit':
            self.smu.setLimit("VOLT", new_value)
        elif path == f'{self.odb_settings_dir}/source/Ilimit':
            self.smu.setLimit("CURR", new_value)

        error = self.smu.getLastError()
        if error[0] != 0:
            self.client.msg(error[1], is_error=True)

    def updateODB(self):
        readback = self.smu.getReadbackSchema()
        settings = self.smu.getSettingsSchema()

        readback['source']['Vrange'] = self.smu.getRange("SOURCE", "VOLT")[0]
        readback['source']['Irange'] = self.smu.getRange("SOURCE", "CURR")[0]
        readback['measure']['voltage'] = self.smu.getVoltage()
        readback['measure']['current'] = self.smu.getCurrent()
        readback['measure']['Vrange'] = self.smu.getRange("SENS", "VOLT")[0]
        readback['measure']['Irange'] = self.smu.getRange("SENS", "CURR")[0] 

        self.client.odb_set(self.odb_readback_dir, readback, remove_unspecified_keys=False)

        settings['ip address'] = self.settings['ip address']
        settings['output'] = self.smu.getOutput()
        settings['terminals'] = self.smu.getTerminals()
        settings['source']['function'] = self.smu.getSource()
        settings['source']['level'] = self.smu.getSourceLevel()
        settings['source']['Vrange'] = self.smu.getRange("SOURCE", "VOLT")[1]
        settings['source']['Irange'] = self.smu.getRange("SOURCE", "CURR")[1]
        settings['source']['Vlimit'] = self.smu.getLimit("VOLT")
        settings['source']['Ilimit'] = self.smu.getLimit("CURR")
        settings['measure']['Vrange'] = self.smu.getRange("SENS", "VOLT")[1]
        settings['measure']['Irange'] = self.smu.getRange("SENS", "CURR")[1]

        if(settings != self.settings):
            local_settings = flatten_dict(settings)
            odb_settings = flatten_dict(self.settings)
            for k,v in local_settings.items():
                if local_settings[k] != odb_settings[k]:
                    self.client.odb_set(f'{self.odb_settings_dir}/{k}', v, remove_unspecified_keys=False)

class SMUFrontend(midas.frontend.FrontendBase):

    def __init__(self, model):
        if(midas.frontend.frontend_index == -1):
            print("E: set frontend index with -i option")
            sys.exit(-1)
        midas.frontend.FrontendBase.__init__(self, f"SMU-{model}-{str(midas.frontend.frontend_index).zfill(2)}")
        self.add_equipment(SMU(self.client, model))

if __name__ == "__main__":
    parser = midas.frontend.parser
    parser.add_argument("--model", required=True, choices = [m.value[0] for m in SMUModel])
    args = midas.frontend.parse_args()

    equip_name = f'SMU-{args.model}-{str(midas.frontend.frontend_index).zfill(2)}'

    # check if a SMU frontend is running with same model and id
    c = midas.client.MidasClient("smu")

    if c.odb_exists(f"/Equipment/{equip_name}/Common/Frontend name"):
        fename = c.odb_get(f"/Equipment/{equip_name}/Common/Frontend name")

        clients = c.odb_get(f'/System/Clients', recurse_dir=False)
        for cid in clients:
            client_name = ""
            try:
                client_name = c.odb_get(f'/System/Clients/{cid}/Name')
            except Exception as e:
                continue

            if client_name == fename:
                c.msg(f"{equip_name} already running on MIDAS server, please change frontend index")
                sys.exit(-1)

    c.odb_delete("/Programs/smu")
    c.disconnect()

    fe = SMUFrontend(args.model)
    fe.run()
