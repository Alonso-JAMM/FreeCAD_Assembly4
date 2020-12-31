import FreeCAD as App
from .HyperDual import HyperDualQuaternion, hdsin, hdcos
from math import pi


class Equality:
    """ Two variables have the same value """
    @staticmethod
    def getVariables(f, varData):
        """ Adds unique variables names to the x names list for the solver
        """
        for axis in f.Components["Base"]:
            if not f.Components["Base"][axis]["enable"]:
                continue
            objName = f.Components["Base"][axis]["obj1Name"]
            refName = f.Components["Base"][axis]["obj2Name"]
            if objName not in varData["variables"]:
                varData["variables"][objName] = Variable()
                varData["variables"][objName]["equal"] = refName
            if refName not in varData["variables"]:
                varData["variables"][refName] = Variable()
        for axis in f.Components["Rotation"]:
            if not f.Components["Rotation"][axis]["enable"]:
                continue
            objName = f.Components["Rotation"][axis]["obj1Name"]
            refName = f.Components["Rotation"][axis]["obj2Name"]
            if objName not in varData["variables"]:
                varData["variables"][objName] = Variable()
                varData["variables"][objName]["equal"] = refName
            if refName not in varData["variables"]:
                varData["variables"][refName] = Variable()
        for comp in f.Components:
            for axis in f.Components[comp]:
                if not f.Components[comp][axis]["enable"]:
                    continue
                xName = f.Components[comp][axis]["obj1Name"]
                rName = f.Components[comp][axis]["obj2Name"]
                rVal = None
                component = rName.split(".")[2]
                placement = rName.split(".")[1]

                if placement == "Rotation":
                    if component == "x":
                        rVal = App.ActiveDocument.getObject(f.Object_2) \
                                  .Placement.Rotation.toEuler()[2] * pi/180
                    elif component == "y":
                        rVal = App.ActiveDocument.getObject(f.Object_2) \
                                  .Placement.Rotation.toEuler()[1] * pi/180
                    elif component == "z":
                        rVal = App.ActiveDocument.getObject(f.Object_2) \
                                  .Placement.Rotation.toEuler()[0] * pi/180
                elif placement == "Base":
                    rVal = getattr(App.ActiveDocument.getObject(f.Object_2)
                                      .Placement.Base, component)

                varData["variables"][xName]["currentValue"] = rVal
                varData["variables"][rName]["currentValue"] = rVal


class Lock:
    """ Lock a variable"""

    @staticmethod
    def getVariables(f, varData):
        for axis in f.Components["Base"]:
            if not f.Components["Base"][axis]["enable"]:
                continue
            objName = f.Components["Base"][axis]["objName"]
            if objName not in varData["variables"]:
                varData["variables"][objName] = Variable()
                varData["variables"][objName]["locked"] = True
        for axis in f.Components["Rotation"]:
            if not f.Components["Rotation"][axis]["enable"]:
                continue
            objName = f.Components["Rotation"][axis]["objName"]
            if objName not in varData["variables"]:
                varData["variables"][objName] = Variable()
                varData["variables"][objName]["locked"] = True
        for comp in f.Components:
            for axis in f.Components[comp]:
                if not f.Components[comp][axis]["enable"]:
                    continue
                xName = f.Components[comp][axis]["objName"]
                c = f.Components[comp][axis]["value"]
                varData["variables"][xName]["currentValue"] = c


class Fix:
    """ A variable is fixed to a value """
    def __init__(self, indexList, fixType, varData):
        # indexList contains the indeces of the variables needed to
        # create the placements of the object and the reference
        # fixType is the type of fix (Rotation or Base)
        self.Ftype = "Fix"
        self.indexList = indexList
        self.fixType = fixType
        self.varData = varData

    def eval(self, x):
        if self.fixType == "Base":
            return self.evalBase(x)
        # quaternion representing the fix rotation
        fqrotx = None
        fqroty = None
        fqrotz = None

        oqrotxIndex = self.indexList["Rotation"]["x"]["Object"]
        oqrotyIndex = self.indexList["Rotation"]["y"]["Object"]
        oqrotzIndex = self.indexList["Rotation"]["z"]["Object"]

        # we don't care about the axis, just the rotation
        rqIndex = self.indexList["Rotation"]["x"]["Reference"][:-2]
        oqIndex = self.indexList["Rotation"]["x"]["Object"][:-2]

        oqx = self.varData["variables"][oqrotxIndex]["q"]
        oqy = self.varData["variables"][oqrotyIndex]["q"]
        oqz = self.varData["variables"][oqrotzIndex]["q"]

        if self.indexList["Rotation"]["x"]["Enable"]:
            fqrotx = self.indexList["Rotation"]["x"]["FixVal"]
        else:
            fqrotx = oqx
        if self.indexList["Rotation"]["y"]["Enable"]:
            fqroty = self.indexList["Rotation"]["y"]["FixVal"]
        else:
            fqroty = oqy
        if self.indexList["Rotation"]["z"]["Enable"]:
            fqrotz = self.indexList["Rotation"]["z"]["FixVal"]
        else:
            fqrotz = oqz
        rq = self.varData["placements"][rqIndex]
        oq = self.varData["placements"][oqIndex]
        fqrot = fqrotz@fqroty@fqrotx
        if self.fixType == "Base":
            baseResult = self.evalBase(x)
            return baseResult
        # First, fill up the rotation objects
        if self.fixType == "Rotation":
            result = rq**-1@oq@fqrot**-1
            return result  # .q0**2 + result.q1**2 + result.q2**2

    def evalBase(self, x):
        """ Evaluates the error function for Base fix. That is, for positions.
        """
        # quaternion representing the fix base
        fqbasex = None
        fqbasey = None
        fqbasez = None
        # Getting the indeces of the Base placements
        pxIndex = self.indexList["Base"]["x"]["Object"]
        pyIndex = self.indexList["Base"]["y"]["Object"]
        pzIndex = self.indexList["Base"]["z"]["Object"]

        # We don't care about the axis, just the overall rotation
        rqIndex = self.indexList["Rotation"]["x"]["Reference"][:-2]

        # we only care about the overall base placement
        pIndex = self.indexList["Base"]["x"]["Object"][:-2]
        rpIndex = self.indexList["Base"]["x"]["Reference"][:-2]
        px = self.varData["variables"][pxIndex]["value"]
        py = self.varData["variables"][pyIndex]["value"]
        pz = self.varData["variables"][pzIndex]["value"]

        if self.indexList["Base"]["x"]["Enable"]:
            fqbasex = self.indexList["Base"]["x"]["FixVal"]
        else:
            fqbasex = px
        if self.indexList["Base"]["y"]["Enable"]:
            fqbasey = self.indexList["Base"]["y"]["FixVal"]
        else:
            fqbasey = py
        if self.indexList["Base"]["z"]["Enable"]:
            fqbasez = self.indexList["Base"]["z"]["FixVal"]
        else:
            fqbasez = pz

        p = self.varData["placements"][pIndex]
        rp = self.varData["placements"][rpIndex]
        fqbase = HyperDualQuaternion(fqbasex, fqbasey, fqbasez, 0)
        refRot = self.varData["placements"][rqIndex]

        # https://fgiesen.wordpress.com/2019/02/09/rotating-a-single-vector-using-a-quaternion/
        q = refRot**-1
        v = p - rp
        t = HyperDualQuaternion(2*(q.q1*v.q2 - q.q2*v.q1),
                                2*(q.q2*v.q0 - q.q0*v.q2),
                                2*(q.q0*v.q1 - q.q1*v.q0),
                                0)
        t2 = HyperDualQuaternion(q.q1*t.q2 - q.q2*t.q1,
                                 q.q2*t.q0 - q.q0*t.q2,
                                 q.q0*t.q1 - q.q1*t.q0,
                                 0)
        t3 = HyperDualQuaternion(t.q0*q.q3,
                                 t.q1*q.q3,
                                 t.q2*q.q3,
                                 0)
        baseEval = v + t3 + t2 - fqbase
        # If an axis is disabled, then we don't care about the value of that
        # axis.
        result = 0
        if self.indexList["Base"]["x"]["Enable"]:
            result += baseEval.q0**2
        if self.indexList["Base"]["y"]["Enable"]:
            result += baseEval.q1**2
        if self.indexList["Base"]["z"]["Enable"]:
            result += baseEval.q2**2
        return result

    def evalRotation(self):
        """ Evaluates the error function for Rotation fix."""
        pass

    @classmethod
    def makeConstraintBase(cls, f, varData):
        """
        Looks for new variables of base constraint to be added to the
        variable list.
        f: a particular fix constraint containing information about the
        object to be fixed.
        varData: containts information about the variables to be used by
        the solver.
        """
        Axes = f.Components["Base"]
        # Stores the indices of the variables used to construct the
        # placements of the object and the reference
        indices = IndexList()

        if (Axes["x"]["enable"] is False and Axes["y"]["enable"] is False
                and Axes["z"]["enable"] is False):
            return

        for axis in Axes:
            xName = Axes[axis]["objName"]
            rName = Axes[axis]["refName"]
            rRotName = f.Components["Rotation"][axis]["refName"]
            xVal = getattr(App.ActiveDocument.getObject(f.Object)
                           .Placement.Base, axis)
            rVal = getattr(App.ActiveDocument.getObject(f.Reference)
                           .Placement.Base, axis)
            # Get the rotation axis value, change this, it is ugly
            ax = None
            if axis == "x":
                ax = 2
            elif axis == "y":
                ax = 1
            elif axis == "z":
                ax = 0
            rRotVal = App.ActiveDocument.getObject(f.Reference) \
                         .Placement.Rotation.toEuler()[ax] * pi/180

            if rRotVal < 0:
                rRotVal = 2*pi + rRotVal

            xIndex = varData["variables"][xName]["index"]
            rIndex = varData["variables"][rName]["index"]
            rRotIndex = varData["variables"][rRotName]["index"]

            indices["Base"][axis]["Object"] = xName
            indices["Base"][axis]["Reference"] = rName
            indices["Rotation"][axis]["Reference"] = rRotName
            indices["Base"][axis]["Enable"] = Axes[axis]["enable"]
            indices["Base"][axis]["FixVal"] = Axes[axis]["value"]

            if xIndex is not None:
                if varData["xList"][xIndex] is None:
                    varData["xList"][xIndex] = xVal
                    varData["variables"][xName]["currentValue"] = xVal
            if rIndex is not None:
                if varData["xList"][rIndex] is None:
                    varData["xList"][rIndex] = rVal
                    varData["variables"][rName]["currentValue"] = rVal
            if rRotIndex is not None:
                if varData["xList"][rRotIndex] is None:
                    varData["xList"][rRotIndex] = rRotVal
                    varData["variables"][rRotName]["currentValue"] = rRotVal

        baseConstraint = cls(indices, "Base", varData)
        varData["fList"].append(baseConstraint)

    @classmethod
    def makeConstraintRotation(cls, f, varData):
        """
        Looks for new variables of rotation constraint to be added to the
        variable list.
        f: a particular fix constraint containing information about the
        object to be fixed.
        varData: contains information about the variables to be used by
        the solver.
        """
        Axes = f.Components["Rotation"]
        # Stores the indices of the variables used to construct the
        # placements of the object and the reference. Note that for
        # rotations, the tree axes are not indenpendent.
        indices = IndexList()

        if (Axes["x"]["enable"] is False and Axes["y"]["enable"] is False
                and Axes["z"]["enable"] is False):
            return

        for axis in Axes:
            xName = Axes[axis]["objName"]
            rName = Axes[axis]["refName"]
            xIndex = varData["variables"][xName]["index"]
            rIndex = varData["variables"][rName]["index"]
            rVal = None
            xVal = None

            fixAngle = Axes[axis]["value"]*pi/180
            fixVal = None

            if axis == "x":
                xVal = App.ActiveDocument.getObject(f.Object) \
                          .Placement.Rotation.toEuler()[2] * pi/180
                rVal = App.ActiveDocument.getObject(f.Reference) \
                          .Placement.Rotation.toEuler()[2] * pi/180
                fixVal = HyperDualQuaternion(hdsin(fixAngle*0.5),
                                             0,
                                             0,
                                             hdcos(fixAngle*0.5))
            elif axis == "y":
                xVal = App.ActiveDocument.getObject(f.Object) \
                          .Placement.Rotation.toEuler()[1] * pi/180
                rVal = App.ActiveDocument.getObject(f.Reference) \
                          .Placement.Rotation.toEuler()[1] * pi/180
                fixVal = HyperDualQuaternion(0,
                                             hdsin(fixAngle*0.5),
                                             0,
                                             hdcos(fixAngle*0.5))
            elif axis == "z":
                xVal = App.ActiveDocument.getObject(f.Object) \
                          .Placement.Rotation.toEuler()[0] * pi/180
                rVal = App.ActiveDocument.getObject(f.Reference) \
                          .Placement.Rotation.toEuler()[0] * pi/180
                fixVal = HyperDualQuaternion(0,
                                             0,
                                             hdsin(fixAngle*0.5),
                                             hdcos(fixAngle*0.5))

            indices["Rotation"][axis]["Object"] = xName
            indices["Rotation"][axis]["Reference"] = rName
            indices["Rotation"][axis]["Enable"] = Axes[axis]["enable"]
            indices["Rotation"][axis]["FixVal"] = fixVal

            # FreeCAD returns negative angles when they are larger than 180 degrees
            if rVal < 0:
                rVal = 2*pi + rVal
            if xVal < 0:
                xVal = 2*pi + xVal

            if xIndex:
                if varData["xList"][xIndex] is None:
                    varData["xList"][xIndex] = xVal
                    varData["variables"][xName]["currentValue"] = xVal
            if rIndex:
                if varData["xList"][rIndex] is None:
                    varData["xList"][rIndex] = rVal
                    varData["variables"][rName]["currentValue"] = rVal

        rotationConstraint = cls(indices, "Rotation", varData)
        varData["fList"].append(rotationConstraint)

    @staticmethod
    def getVariables(f, varData):
        """ Adds unique variables names to the x names list for the solver.
        f: a particular fix constraint
        varData: data of the variables used by the constraints
        """
        objBase = f.Object + ".Base"
        refBase = f.Reference + ".Base"
        refRotation = f.Reference + ".Rotation"
        if objBase not in varData["placements"]:
            varData["placements"][objBase] = None
        if refBase not in varData["placements"]:
            varData["placements"][refBase] = None
        if refRotation not in varData["placements"]:
            varData["placements"][refRotation] = None
        for axis in f.Components["Base"]:
            objName = f.Components["Base"][axis]["objName"]
            refName = f.Components["Base"][axis]["refName"]
            refRotName = f.Components["Rotation"][axis]["refName"]
            # Creating the variables objects
            if objName not in varData["variables"]:
                varData["variables"][objName] = Variable()
            if refName not in varData["variables"]:
                varData["variables"][refName] = Variable()
            if refRotName not in varData["variables"]:
                varData["variables"][refRotName] = Variable()

        Axes = f.Components["Rotation"]
        # There are some situations in which the rotation of the object
        # (not the reference) is not needed. Like in base fix constraint
        if (Axes["x"]["enable"] is False and Axes["y"]["enable"] is False
                and Axes["x"]["enable"] is False):
            return
        objRotation = f.Object + ".Rotation"
        if objRotation not in varData["placements"]:
            varData["placements"][objRotation] = None
        for axis in f.Components["Rotation"]:
            objName = f.Components["Rotation"][axis]["objName"]
            refName = f.Components["Rotation"][axis]["refName"]
            # Creating the variables objects
            if objName not in varData["variables"]:
                varData["variables"][objName] = Variable()
            if refName not in varData["variables"]:
                varData["variables"][refName] = Variable()


class Variable(dict):
    """ Stores the information about the variables used in the assembly.
    Variable objects are stored in the varData dictionary. Note that the
    name of the variable will be the key of the variable object in the
    varData dictionary.
    """
    def __init__(self):
        super().__init__()
        # Stores the index corresponding to the variable position inside the
        # scipy solver array
        self["index"] = None
        # Indicates whether this variable is locked (a lock constraint is
        # applied to this variable)
        self["locked"] = False
        # A hyperdual or a float depending on whether the variable is locked
        # or not. If this is a hyperdual value, then it should be exactly the
        # same object than the corresponding hyperdual in self.x inside the
        # solver object
        self["value"] = None
        # currentValue stores the value of the object at the beginning of the
        # solving procedure
        self["currentValue"] = None
        # The name of the reference variable we want this variable to have
        # the exact same value or None.
        # If we set this variable equal to another, then the value of this
        # variable will be the same exact object than the other variable
        self["equal"] = None
        # quaternion representation of the rotation about the global axis
        # corresponding to this variable (useful for angle variables which
        # represent rotations about the global axes)
        self["q"] = None


class IndexList(dict):
    """ Stores the indices of the variables to construct the placements
    of the object and reference while performing the error calculations
    """
    def __init__(self):
        super().__init__()
        self["Base"] = {
                "x": {
                    "Object": None,
                    "Reference": None,
                    "Enable": False,
                    "FixVal": None,
                    },
                "y": {
                    "Object": None,
                    "Reference": None,
                    "Enable": False,
                    "FixVal": None,
                    },
                "z": {
                    "Object": None,
                    "Reference": None,
                    "Enable": False,
                    "FixVal": None,
                    }

        }
        self["Rotation"] = {
                "x": {
                    "Object": None,
                    "Reference": None,
                    "Enable": False,
                    "FixVal": None,
                    },
                "y": {
                    "Object": None,
                    "Reference": None,
                    "Enable": False,
                    "FixVal": None,
                    },
                "z": {
                    "Object": None,
                    "Reference": None,
                    "Enable": False,
                    "FixVal": None,
                    }
        }
