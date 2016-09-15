import subprocess
import sys
import os
import errno
import random
import copy

# Make sure $SUMO_HOME/tools is in $PYTHONPATH
from sumolib import checkBinary
import traci
import traci.constants as tc

import config as defaults
from makecirc import makecirc, makenet
from parsexml import parsexml
from plots import pcolor, pcolor_multi


KNOWN_PARAMS = {
        "maxSpeed"      : traci.vehicletype.setMaxSpeed,
        "accel"         : traci.vehicletype.setAccel,
        "decel"         : traci.vehicletype.setDecel,
        "sigma"         : traci.vehicletype.setImperfection,
        "tau"           : traci.vehicletype.setTau,
        "speedFactor"   : traci.vehicletype.setSpeedFactor,
        "speedDev"      : traci.vehicletype.setSpeedDeviation,
        }

def ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    return path

class LoopSim:

    def __init__(self, name, length, numLanes, 
            maxSpeed=defaults.SPEED_LIMIT, port=defaults.PORT):
        self.name = "%s-%dm%dl" % (name, length, numLanes)
        self.length = length
        self.numLanes = numLanes

        edgelen = length/4.
        self.edgestarts = {"bottom": 0, 
                           "right": edgelen, 
                           "top": 2*edgelen, 
                           "left": 3*edgelen}

        self._mkdirs(name)
        # Make loop network
        self.netfn = makenet(self.name, 
                length=self.length, 
                lanes=self.numLanes,
                maxSpeed=maxSpeed,
                path=self.net_path)
        self.port = port

    def _mkdirs(self, name):
        self.net_path = ensure_dir("%s" % defaults.NET_PATH)
        self.data_path = ensure_dir("%s" % defaults.DATA_PATH)
        self.img_path = ensure_dir("%s" % defaults.IMG_PATH)

    def _simInit(self, suffix, typeList):
        self.cfgfn, self.outs = makecirc(self.name+suffix, 
                netfn=self.netfn, 
                numcars=0, 
                typelist=typeList,
                dataprefix = defaults.DATA_PATH)

        # Start simulator
        sumoBinary = checkBinary('sumo')
        self.sumoProcess = subprocess.Popen([
                sumoBinary, 
                "--step-length", repr(defaults.SIM_STEP_LENGTH),
                "--no-step-log",
                "-c", self.cfgfn,
                "--remote-port", str(self.port)], 
            stdout=sys.stdout, stderr=sys.stderr)

        # Initialize TraCI
        traci.init(self.port)

    def _getEdge(self, x):
        for (e, s) in self.edgestarts.iteritems():
            if x >= s:
                starte = e
                startx = x-s
        return starte, startx

    def _getX(self, edge, position):
        return position + self.edgestarts[edge]

    def _addTypes(self, paramsList):
        self.maxSpeed = 0
        self.carFns = {}

        for params in paramsList:
            name = params["name"]
            self.carFns[name] = params.get("function", None)
            maxSpeed = params.get("maxSpeed", defaults.SPEED_LIMIT)

            for (pname, pvalue) in params.iteritems():
                if pname in KNOWN_PARAMS:
                    KNOWN_PARAMS[pname](name, pvalue)

            self.maxSpeed = max(self.maxSpeed, maxSpeed)

    def _createCar(self, name, x, vtype, lane):
        starte, startx = self._getEdge(x)
        traci.vehicle.addFull(name, "route"+starte, typeID=vtype)
        traci.vehicle.moveTo(name, starte + "_" + repr(lane), startx)

    def _addCars(self, paramsList):
        cars = {}
        self.numCars = 0

        # Create car list
        for param in paramsList:
            self.numCars += param["count"]
            for i in range(param["count"]):
                vtype = param["name"]
                laneSpread = param.get("laneSpread", True)
                carname = "%s-%03d" % (vtype, i)
                cars[carname] = (vtype, laneSpread)

        lane = 0
        carsitems = cars.items()
        # Add all cars to simulation ...
        random.shuffle(carsitems) # randomly
        for i, (carname, (vtype, laneSpread)) in enumerate(carsitems):
            x = self.length * i / self.numCars
            self._createCar(carname, x, vtype, 
                    lane if laneSpread is True else laneSpread)
            lane = (lane + 1) % self.numLanes

        self.carNames = cars.keys()

    def _run(self, simSteps):
        for step in range(simSteps):
            traci.simulationStep()
            self.allCars = []
            for v in self.carNames:
                car = {}
                car["id"] = v
                car["type"] = traci.vehicle.getTypeID(v)
                car["edge"] = traci.vehicle.getRoadID(v)
                position = traci.vehicle.getLanePosition(v)
                car["lane"] = traci.vehicle.getLaneIndex(v)
                car["x"] = self._getX(car["edge"], position)
                car["v"] = traci.vehicle.getSpeed(v)
                self.allCars.append(car)
            self.allCars.sort(key=lambda x: x["x"])

            for (idx, car) in enumerate(self.allCars):
                carFn = self.carFns[car["type"]]
                if carFn is not None:
                    carFn((idx, car), self, step)

        traci.close()
        sys.stdout.flush()
        self.sumoProcess.wait()

    def getCars(self, idx, numBack = None, numForward = None, 
                           dxBack = None, dxForward = None,
                           lane = None):
        ret = []
        x = self.allCars[idx]["x"]

        for i in range(idx-1, -1, -1) + range(self.numCars-1, idx, -1):
            c = self.allCars[i]
            if (dxBack is not None and (x - c["x"]) % self.length > dxBack) or \
               (numBack is not None and len(ret) >= numBack):
                    break
            if (lane is None or c["lane"] == lane):
                    ret.insert(0, c)

        cnt = len(ret)

        for i in range(idx+1, self.numCars) + range(0, idx):
            c = self.allCars[i]
            if (dxForward is not None and (c["x"]-x) % self.length > dxForward) or \
               (numForward is not None and (len(ret) - cnt) >= numForward):
                    break
            if (lane is None or c["lane"] == lane):
                    ret.append(c)

        return ret


    def simulate(self, opts):

        self.label = opts.get("label", None)
        tag = opts.get("tag", None)

        paramsList = opts["paramsList"]
        self.simSteps = opts.get("simSteps", 500)

        if self.label is None:
            self.label = "-".join([x["name"] + "%03d" % x["count"] 
                                        for x in paramsList 
                                        if x["count"] > 0])
        if tag is not None:
            self.label += "-" + tag

        self._simInit("-" + self.label, [x["name"] for x in paramsList])
        self._addTypes(paramsList)
        self._addCars(paramsList)
        self._run(self.simSteps)

    def plot(self, show=True, save=False):
        # Plot results
        nsfn = self.outs["netstate"]
        alldata, trng, xrng, speeds, lanespeeds = parsexml(nsfn, self.edgestarts, self.length)

        print "Generating interpolated plot..."
        plt = pcolor_multi("Traffic jams (%d lanes, %s)" % (self.numLanes, self.label), 
                (xrng, "Position along loop (m)"),
                (trng, "Time (s)"),
                (lanespeeds, 0, self.maxSpeed, "Speed (m/s)"))

        fig = plt.gcf()
        if show:
            plt.show()
        if save:
            fig.savefig(defaults.IMG_PATH + self.name + "-" + self.label + ".png")
        return plt

# this is the main entry point of this script
if __name__ == "__main__":
    from carfns import randomChangeLaneFn, ACCFnBuilder, changeFasterLaneBuilder, MidpointFnBuilder, SwitchFn

    humanParams = {
            "name"        : "human",
            "count"       :  0,
            "maxSpeed"    :  40,
            "accel"       :   2.6,
            "decel"       :   4.5,
            # "function"    : randomChangeLaneFn,
            # "function"    : changeFasterLaneBuilder(),
            "laneSpread"  : 0,
            "speedFactor" : 1.0,
            "speedDev"    : 0.1,
            "sigma"       : 0.5,
            "tau"         : 3, # http://www.croberts.com/respon.htm
            "laneChangeModel": 'LC2013',
            }

    robotParams = {
        "name"        : "robot",
        "count"       :  0,
        "maxSpeed"    :  40,
        "accel"       :   4,
        "decel"       :   6,
        # "function"    : MidpointFnBuilder(max_speed=40, gain=0.1, beta=0.9, duration=250, bias=1.0, ratio=0.25),
        "function"    : ACCFnBuilder(follow_sec=1.0, max_speed=40, gain=0.1, beta=0.9),
        "laneSpread"  : 0,
        "tau"         : 0.5,
    }

    hybridParams = copy.copy(humanParams)
    hybridParams["name"] = "hybrid"
    hybridParams["count"] = 30
    hybridParams["function"] = SwitchFn("robot", 0.5, initCarFn=randomChangeLaneFn)

    opts = {
            "paramsList" : [humanParams, robotParams, hybridParams],
            "simSteps"   : 500,
            "tag"        : "Hybrid"
            }

    defaults.SIM_STEP_LENGTH = 0.5
    sim = LoopSim("loopsim", length=1000, numLanes=2)
    sim.simulate(opts)
    sim.plot(show=True, save=True)
