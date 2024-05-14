from enum import Enum

class SMUDevice:
    def __init__(self, session):
        self.session = session

    def query(self, cmd):
        res = ""
        #print(f'Q: {cmd}')
        try:
            res = self.session.query(cmd)
        except Exception as e:
            print(f'E: {e}')

        return res

    def write(self, cmd):
        #print(f'W: {cmd}')
        try:
            self.session.write(cmd)
        except Exception as e:
            print(f'E: {e}')

    def reset(self):
        self.write("*RST")

class SMUModel(Enum):
    K2450 = '2450',

class SMUKeithley2450(SMUDevice):
    def __init__(self, session):
        super().__init__(session)

        self.sourcelist = [ 'VOLT', 'CURR' ]
        self.senselist = [ 'VOLT:DC', 'CURR:DC', 'RES']

        self.vrange = [ '0.02', '0.2', '2', '20', '200' ]
        self.vrangestr = [ '20mV', '200mV', '2V', '20V', '200V' ]

        self.irange = [ '1E-08', '1E-07', '1E-06', '1E-05', '0.0001', '0.001', '0.01', '0.1', '1' ]
        self.irangestr = [ '10nA', '100nA', '1uA', '10uA', '100uA', '1mA', '10mA', '100mA', '1A' ]

        self.model = SMUModel.K2450
        self.modelname = "2450"
        self.brand = "Keithley"

        self.settings = {
            "brand" : self.brand,
            "model": self.modelname,
            "output": False,
        }

        self.readback = {
            "source Vrange" : "",
            "source Irange" : "",
            "sense Vrange" : "",
            "sense Irange" : "",
        }

        self.source = ""

        self.reset()

    def getSettingsSchema(self):
        self.settings["source"] = ""
        self.settings["source level"] = 0.0
        self.settings["sense"] = ""
        self.settings["sense level"] = 0.0
        self.settings["source Vrange"] = ""
        self.settings["source Irange"] = ""
        self.settings["sense Vrange"] = ""
        self.settings["sense Irange"] = ""
        self.settings["last error"] = ""
        return self.settings

    def getReadbackSchema(self):
        return self.readback

    # SOURCE 

    def setSource(self, value):
        if value in self.sourcelist:
            self.write(f":SOURCE:FUNC {value}")

    def getSource(self):
        self.source = self.query(":SOURCE:FUNC?")
        return self.source

    def setSourceLevel(self, value):
        self.write(f":SOURCE:{self.source}:LEV {value}")

    def getSourceLevel(self):
        return self.query(f":SOURCE:{self.source}:LEV?")

    # SOURCE voltage range

    def setSourceVoltageRange(self, vrange):
        if str.lower(vrange) == 'auto':
            self.write(":SOURCE:VOLT:RANG:AUTO ON")
        elif vrange in self.vrangestr:
            i = self.vrangestr.index(vrange)
            self.write(f":SOURCE:VOLT:RANG {self.vrange[i]}")

    def getSourceVoltageRange(self):
        vrange = self.query(":SOURCE:VOLT:RANG?")
        if vrange in self.vrange:
            i = self.vrange.index(vrange)
            if int(self.query(":SOURCE:VOLT:RANG:AUTO?")) == 1:
                return (self.vrangestr[i], "auto")
            else: 
                return (self.vrangestr[i], self.vrangestr[i])

    # SOURCE current range

    def setSourceCurrentRange(self, irange):
        if str.lower(irange) == 'auto':
            self.write(":SOURCE:CURR:RANGE:AUTO ON")
        elif irange in self.irangestr:
            i = self.irangestr.index(irange)
            self.write(f":SOURCE:CURR:RANG {self.irange[i]}")

    def getSourceCurrentRange(self):
        irange = self.query(":SOURCE:CURR:RANG?")
        if irange in self.irange:
            i = self.irange.index(irange)
            if int(self.query(":SOURCE:CURR:RANG:AUTO?")) == 1:
                return (self.irangestr[i], "auto")
            else:
                return (self.irangestr[i], self.irangestr[i])

def SMUFactory(model, session):
    if model not in [m.value[0] for m in SMUModel]:
        raise TypeError
    if model == '2450':
        return SMUKeithley2450(session)


