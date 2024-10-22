from enum import Enum

class SMUDevice:
    def __init__(self):
        self.session = None

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
        #self.write("*RST")
        self.write("*CLS")

    def setSession(self, session):
        self.session = session

class SMUModel(Enum):
    K2450 = '2450',

class SMUKeithley2450(SMUDevice):
    def __init__(self):
        super().__init__()

        self.sourcelist = [ 'VOLT', 'CURR' ]
        self.measurelist = [ '"VOLT:DC"', '"CURR:DC"', '"RES"']
        self.termlist = [ 'FRON', 'REAR' ]

        self.vrange = [ '0.02', '0.2', '2', '20', '200' ]
        self.vrangestr = [ '20mV', '200mV', '2V', '20V', '200V' ]

        self.irange = [ '1E-08', '1E-07', '1E-06', '1E-05', '0.0001', '0.001', '0.01', '0.1', '1' ]
        self.irangestr = [ '10nA', '100nA', '1uA', '10uA', '100uA', '1mA', '10mA', '100mA', '1A' ]


        self.model = SMUModel.K2450
        self.modelname = "2450"
        self.brand = "Keithley"

        self.settings = {
            "ip address" : "",
            "brand" : self.brand,
            "model": self.modelname,
            "output": False,
            "terminals" : "",
            "source" : {
                "function" : "",
                "level" : 0.0,
                "Vrange" : "",
                "Irange" : "",
                "Vlimit" : 0.0,
                "Ilimit" : 0.0,
            },
            "measure" : {
                "Vrange" : "",
                "Irange" : "",
            },
        }

        self.readback = {
            "source" : {
                "Vrange" : "",
                "Irange" : "",
            },
            "measure" : {
                "voltage" : 0.0,
                "current" : 0.0,
                "Vrange" : "",
                "Irange" : "",
            },
            "last error" : "",
        }

        self.source = ""

    def getSettingsSchema(self):
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

    # MEASURE

    def setMeasure(self, value):
        if value in self.measurelist:
            self.write(f":SENS:FUNC {value}")

    def getMeasure(self):
        return self.query(":SENS:FUNC?")

    def getMeasureLevel(self):
        return float(self.query(":READ?"))

    def getCurrent(self):
        return float(self.query(":MEAS:CURR:DC?"))

    def getVoltage(self):
        return float(self.query(":MEAS:VOLT:DC?"))

    # GENERIC source/measure voltage/current range

    def setRange(self, direction, function, value):
        if direction != "SOURCE" and direction != "SENS":
            return
        if function == 'CURR':
            if str.lower(value) == 'auto':
                self.write(f":{direction}:CURR:RANG:AUTO ON")
            elif value in self.irangestr:
                i = self.irangestr.index(value)
                self.write(f":{direction}:CURR:RANG {self.irange[i]}")
        elif function == 'VOLT':
            if str.lower(value) == 'auto':
                self.write(f":{direction}:VOLT:RANG:AUTO ON")
            elif value in self.vrangestr:
                i = self.vrangestr.index(value)
                self.write(f":{direction}:VOLT:RANG {self.vrange[i]}")

    def getRange(self, direction, function):
        if direction != "SOURCE" and direction != "SENS":
            return (None, None)
        if function == 'CURR':
            irange = self.query(f":{direction}:CURR:RANG?") 
            if irange in self.irange:
                i = self.irange.index(irange)
                if int(self.query(f":{direction}:CURR:RANG:AUTO?")) == 1:
                    return (self.irangestr[i], "auto")
                else:
                    return (self.irangestr[i], self.irangestr[i])
        elif function == 'VOLT':
            vrange = self.query(f":{direction}:VOLT:RANG?")
            if vrange in self.vrange:
                i = self.vrange.index(vrange)
                if int(self.query(f":{direction}:VOLT:RANG:AUTO?")) == 1:
                    return (self.vrangestr[i], "auto")
                else: 
                    return (self.vrangestr[i], self.vrangestr[i])

    # LIMIT

    def getLimit(self, function):
        if function == 'VOLT':
            return (float(self.query(f':SOUR:CURR:VLIMIT?')))
        elif function == 'CURR':
            return (float(self.query(f':SOUR:VOLT:ILIMIT?')))

    def setLimit(self, function, value):
        if function == 'VOLT':
            self.write(f':SOUR:CURR:VLIMIT {value}')
        elif function == 'CURR':
            self.write(f':SOUR:VOLT:ILIMIT {value}')

    # OUTPUT

    def setOutput(self, value):
        if value in ['ON', 'OFF'] or value in [0, 1]:
            self.write(f':OUTP {value}')

    def getOutput(self):
        return int(self.query(":OUTP?"))

    # TERMINALS

    def setTerminals(self, value):
        if value in self.termlist:
            self.write(f'ROUTE:TERM {value}')

    def getTerminals(self):
        return self.query('ROUTE:TERM?')

    # LOG

    def getLastError(self):
        line = self.query(":SYST:ERR?")
        errorCode = line.split(',')[0]
        return (int(errorCode), line)

def SMUFactory(model):
    if model not in [m.value[0] for m in SMUModel]:
        raise TypeError
    if model == '2450':
        return SMUKeithley2450()


