import random
import copy

# Make sure $SUMO_HOME/tools is in $PYTHONPATH
import traci

from loopsim import LoopSim
from carfns import randomChangeLaneFn, ACCFnBuilder, changeFasterLaneBuilder, MidpointFnBuilder, SwitchFn


if __name__ == "__main__":

    humanParams = {
            "name"        : "human",
            "count"       : 20,
            "maxSpeed"    : 60,
            "laneSpread"  : 0,
            "speedFactor" : 1.0,
            "speedDev"    : 0.1,
            }

    opts = {
            "paramsList" : [humanParams],
            "simSteps"   : 500,
            "tag"        : "simple"
            }

    sim = LoopSim("loopsim", length=1000, numLanes=2, speedLimit=35, simStepLength=0.5)
    sim.simulate(opts)
    sim.plot(show=True, save=True)
