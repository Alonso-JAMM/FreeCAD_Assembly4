import FreeCAD as App
from .HyperDual import HyperDualQuaternion, hdsin, hdcos
from math import pi


class Equality:
    """ Two variables have the same value """
    def __init__(self, a, b):
        # a and b are the positions of the variables to be set equal in the
        # variable array
        self.a = a
        self.b = b
        self.Ftype = "Equality"

    def eval(self, x):
        return x[self.a] - x[self.b]

    @classmethod
    def makeConstraint(cls, f, varData):
        """
        Looks for new variables to be added to the variable lists.
        f: is a particular equality constraint between two datum objects. It
        includes data about which objects are being constrained and which
        parameters of their placements are being set equal.
        x_names: is a list of the current variables already accounted. Note
        that variables need to be unique so this list is needed in order to
        avoid repeated variables in the lists
        x_list: a list of the values of all the variables. The values are
        either a real value or None. This method modifies x_list in place
        (values of the variables are put on x_list in their corresponding
        place)
        returns: an Equality object created with data from f
        """
        for comp in f.Components:
            for axis in f.Components[comp]:
                if not f.Components[comp][axis]["enable"]:
                    continue
                x1Name = f.Components[comp][axis]["obj1Name"]
                x2Name = f.Components[comp][axis]["obj2Name"]
                x1Val = None
                x2Val = None
                x1Index = varData["xNames"].index(x1Name)
                x2Index = varData["xNames"].index(x2Name)
                component = x1Name.split(".")[2]
                placement = x1Name.split(".")[1]

                if placement == "Rotation":
                    if component == "x":
                        x1Val = App.ActiveDocument.getObject(f.Object_1) \
                                    .Placement.Rotation.toEuler()[2] * pi/180
                        x2Val = App.ActiveDocument.getObject(f.Object_2) \
                                   .Placement.Rotation.toEuler()[2] * pi/180
                    elif component == "y":
                        x1Val = App.ActiveDocument.getObject(f.Object_1) \
                                   .Placement.Rotation.toEuler()[1] * pi/180
                        x2Val = App.ActiveDocument.getObject(f.Object_2) \
                                   .Placement.Rotation.toEuler()[1] * pi/180
                    elif component == "z":
                        x1Val = App.ActiveDocument.getObject(f.Object_1) \
                                   .Placement.Rotation.toEuler()[0] * pi/180
                        x2Val = App.ActiveDocument.getObject(f.Object_2) \
                                   .Placement.Rotation.toEuler()[0] * pi/180
                elif placement == "Base":
                    x1Val = getattr(App.ActiveDocument.getObject(f.Object_1)
                                       .Placement.Base, component)
                    x2Val = getattr(App.ActiveDocument.getObject(f.Object_2)
                                       .Placement.Base, component)

                # Modify x_list in place
                if varData["xList"][x1Index] is None:
                    varData["xList"][x1Index] = x1Val
                if varData["xList"][x2Index] is None:
                    varData["xList"][x2Index] = x2Val

                varData["fList"].append(cls(x1Index, x2Index))

    @staticmethod
    def getVariables(f, varData):
        """ Adds unique variables names to the x names list for the solver
        """
        for axis in f.Components["Base"]:
            objName = f.Components["Base"][axis]["obj1Name"]
            refName = f.Components["Base"][axis]["obj2Name"]
            if objName not in varData["xNames"]:
                varData["xNames"].append(objName)
            if refName not in varData["xNames"]:
                varData["xNames"].append(refName)
        for axis in f.Components["Rotation"]:
            objName = f.Components["Rotation"][axis]["obj1Name"]
            refName = f.Components["Rotation"][axis]["obj2Name"]
            if objName not in varData["xNames"]:
                varData["xNames"].append(objName)
            if refName not in varData["xNames"]:
                varData["xNames"].append(refName)


class Lock:
    """ Lock a variable"""
    def __init__(self, a, c):
        self.a = a  # variable to lock
        self.c = c  # set value
        self.Ftype = "Lock"

    def eval(self, x):
        return x[self.a] - self.c

    @classmethod
    def makeConstraint(cls, f, varData):  # f, xNames, xList):
        for comp in f.Components:
            for axis in f.Components[comp]:
                if not f.Components[comp][axis]["enable"]:
                    continue
                xName = f.Components[comp][axis]["objName"]
                xVal = None
                xIndex = varData["xNames"].index(xName)
                component = xName.split(".")[2]
                placement = xName.split(".")[1]
                c = f.Components[comp][axis]["value"]

                if placement == "Rotation":
                    c = c*pi/180
                    if component == "x":
                        xVal = App.ActiveDocument.getObject(f.Object) \
                                  .Placement.Rotation.toEuler()[2] * pi/180
                    elif component == "y":
                        xVal = App.ActiveDocument.getObject(f.Object) \
                                  .Placement.Rotation.toEuler()[1] * pi/180
                    elif component == "z":
                        xVal = App.ActiveDocument.getObject(f.Object) \
                                  .Placement.Rotation.toEuler()[0] * pi/180
                elif placement == "Base":
                    xVal = getattr(App.ActiveDocument.getObject(f.Object)
                                      .Placement.Base, component)

                if varData["xList"][xIndex] is None:
                    varData["xList"][xIndex] = xVal

                varData["fList"].append(cls(xIndex, c))

    @staticmethod
    def getVariables(f, varData):
        for axis in f.Components["Base"]:
            objName = f.Components["Base"][axis]["objName"]
            if objName not in varData["xNames"]:
                varData["xNames"].append(objName)
        for axis in f.Components["Rotation"]:
            objName = f.Components["Rotation"][axis]["objName"]
            if objName not in varData["xNames"]:
                varData["xNames"].append(objName)


class Fix:
    """ A variable is fixed to a value """
    def __init__(self, indexList, fixType):
        # indexList contains the indeces of the variables needed to
        # create the placements of the object and the reference
        # fixType is the type of fix (Rotation or Base)
        self.Ftype = "Fix"
        self.indexList = indexList
        self.fixType = fixType

    def eval(self, x):
        if self.fixType == "Base":
            return self.evalBase(x)
        # quaternion representing the fix rotation
        fqrotxIndex = None
        fqrotyIndex = None
        fqrotzIndex = None
        fqrotx = None
        fqroty = None
        fqrotz = None

        rqrotxIndex = self.indexList["Rotation"]["x"]["Reference"]
        oqrotxIndex = self.indexList["Rotation"]["x"]["Object"]
        rqrotyIndex = self.indexList["Rotation"]["y"]["Reference"]
        oqrotyIndex = self.indexList["Rotation"]["y"]["Object"]
        rqrotzIndex = self.indexList["Rotation"]["z"]["Reference"]
        oqrotzIndex = self.indexList["Rotation"]["z"]["Object"]
        if self.indexList["Rotation"]["x"]["Enable"]:
            val = self.indexList["Rotation"]["x"]["FixVal"]
            fqrotx = HyperDualQuaternion(hdsin(val/2),
                                         0,
                                         0,
                                         hdcos(val/2))
        else:
            fqrotxIndex = self.indexList["Rotation"]["x"]["Object"]
            fqrotx = HyperDualQuaternion(hdsin(x[fqrotxIndex]/2),
                                         0,
                                         0,
                                         hdcos(x[fqrotxIndex]/2))
        if self.indexList["Rotation"]["y"]["Enable"]:
            val = self.indexList["Rotation"]["y"]["FixVal"]
            fqroty = HyperDualQuaternion(0,
                                         hdsin(val/2),
                                         0,
                                         hdcos(val/2))
        else:
            fqrotyIndex = self.indexList["Rotation"]["y"]["Object"]
            fqroty = HyperDualQuaternion(0,
                                         hdsin(x[fqrotyIndex]/2),
                                         0,
                                         hdcos(x[fqrotyIndex]/2))
        if self.indexList["Rotation"]["z"]["Enable"]:
            val = self.indexList["Rotation"]["z"]["FixVal"]
            fqrotz = HyperDualQuaternion(0,
                                         0,
                                         hdsin(val/2),
                                         hdcos(val/2))
        else:
            fqrotzIndex = self.indexList["Rotation"]["z"]["Object"]
            fqrotz = HyperDualQuaternion(0,
                                         0,
                                         hdsin(x[fqrotzIndex]/2),
                                         hdcos(x[fqrotzIndex]/2))

        rqx = HyperDualQuaternion(hdsin((x[rqrotxIndex])/2),
                                  0,
                                  0,
                                  hdcos((x[rqrotxIndex])/2))
        rqy = HyperDualQuaternion(0,
                                  hdsin((x[rqrotyIndex])/2),
                                  0,
                                  hdcos((x[rqrotyIndex])/2))
        rqz = HyperDualQuaternion(0,
                                  0,
                                  hdsin((x[rqrotzIndex])/2),
                                  hdcos((x[rqrotzIndex])/2))
        oqx = HyperDualQuaternion(hdsin(x[oqrotxIndex]/2),
                                  0,
                                  0,
                                  hdcos(x[oqrotxIndex]/2))
        oqy = HyperDualQuaternion(0,
                                  hdsin(x[oqrotyIndex]/2),
                                  0,
                                  hdcos(x[oqrotyIndex]/2))
        oqz = HyperDualQuaternion(0,
                                  0,
                                  hdsin(x[oqrotzIndex]/2),
                                  hdcos(x[oqrotzIndex]/2))
        rq = rqz@rqy@rqx
        oq = oqz@oqy@oqx
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
        rpxIndex = self.indexList["Base"]["x"]["Reference"]
        rpyIndex = self.indexList["Base"]["y"]["Reference"]
        rpzIndex = self.indexList["Base"]["z"]["Reference"]

        rqrotxIndex = self.indexList["Rotation"]["x"]["Reference"]
        rqrotyIndex = self.indexList["Rotation"]["y"]["Reference"]
        rqrotzIndex = self.indexList["Rotation"]["z"]["Reference"]

        rqx = HyperDualQuaternion(hdsin((x[rqrotxIndex])/2),
                                  0,
                                  0,
                                  hdcos((x[rqrotxIndex])/2))
        rqy = HyperDualQuaternion(0,
                                  hdsin((x[rqrotyIndex])/2),
                                  0,
                                  hdcos((x[rqrotyIndex])/2))
        rqz = HyperDualQuaternion(0,
                                  0,
                                  hdsin((x[rqrotzIndex])/2),
                                  hdcos((x[rqrotzIndex])/2))

        if self.indexList["Base"]["x"]["Enable"]:
            fqbasex = self.indexList["Base"]["x"]["FixVal"]
        else:
            fqbasexIndex = self.indexList["Base"]["x"]["Object"]
            fqbasex = x[fqbasexIndex]
        if self.indexList["Base"]["y"]["Enable"]:
            fqbasey = self.indexList["Base"]["y"]["FixVal"]
        else:
            fqbaseyIndex = self.indexList["Base"]["y"]["Object"]
            fqbasey = x[fqbaseyIndex]
        if self.indexList["Base"]["z"]["Enable"]:
            fqbasez = self.indexList["Base"]["z"]["FixVal"]
        else:
            fqbasezIndex = self.indexList["Base"]["z"]["Object"]
            fqbasez = x[fqbasezIndex]
        p = HyperDualQuaternion(x[pxIndex], x[pyIndex], x[pzIndex], 0)
        rp = HyperDualQuaternion(x[rpxIndex].real, x[rpyIndex].real, x[rpzIndex].real, 0)
        fqbase = HyperDualQuaternion(fqbasex, fqbasey, fqbasez, 0)
        refRot = rqz@rqy@rqx

        baseEval = refRot**-1@(p-rp)@refRot - fqbase
        # If an axis is disabled, then we don't care about the value of that
        # axis.
        result = baseEval.q3**2

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

        for axis in Axes:
            xName = Axes[axis]["objName"]
            rName = Axes[axis]["refName"]
            rRotName = f.Components["Rotation"][axis]["refName"]
            xVal = getattr(App.ActiveDocument.getObject(f.Object)
                           .Placement.Base, axis)
            rVal = getattr(App.ActiveDocument.getObject(f.Reference)
                           .Placement.Base, axis)
            xIndex = varData["xNames"].index(xName)
            rIndex = varData["xNames"].index(rName)
            rRotIndex = varData["xNames"].index(rRotName)

            indices["Base"][axis]["Object"] = xIndex
            indices["Base"][axis]["Reference"] = rIndex
            indices["Rotation"][axis]["Reference"] = rRotIndex
            indices["Base"][axis]["Enable"] = Axes[axis]["enable"]
            indices["Base"][axis]["FixVal"] = Axes[axis]["value"]
            indices["Base"]["Reference"] = rName

            if varData["xList"][xIndex] is None:
                varData["xList"][xIndex] = xVal
            if varData["xList"][rIndex] is None:
                varData["xList"][rIndex] = rVal

        if (Axes["x"]["enable"] is False and Axes["y"]["enable"] is False
                and Axes["z"]["enable"] is False):
            return

        baseConstraint = cls(indices, "Base")
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

        for axis in Axes:
            xName = Axes[axis]["objName"]
            rName = Axes[axis]["refName"]
            xIndex = varData["xNames"].index(xName)
            rIndex = varData["xNames"].index(rName)
            rVal = None
            xVal = None

            if axis == "x":
                xVal = App.ActiveDocument.getObject(f.Object) \
                          .Placement.Rotation.toEuler()[2] * pi/180
                rVal = App.ActiveDocument.getObject(f.Reference) \
                          .Placement.Rotation.toEuler()[2] * pi/180
            elif axis == "y":
                xVal = App.ActiveDocument.getObject(f.Object) \
                          .Placement.Rotation.toEuler()[1] * pi/180
                rVal = App.ActiveDocument.getObject(f.Reference) \
                          .Placement.Rotation.toEuler()[1] * pi/180
            elif axis == "z":
                xVal = App.ActiveDocument.getObject(f.Object) \
                          .Placement.Rotation.toEuler()[0] * pi/180
                rVal = App.ActiveDocument.getObject(f.Reference) \
                          .Placement.Rotation.toEuler()[0] * pi/180

            indices["Rotation"][axis]["Object"] = xIndex
            indices["Rotation"][axis]["Reference"] = rIndex
            indices["Rotation"][axis]["Enable"] = Axes[axis]["enable"]
            indices["Rotation"][axis]["FixVal"] = Axes[axis]["value"]*pi/180

            # FreeCAD returns negative angles when they are larger than 180 degrees
            if rVal < 0:
                rVal = 2*pi + rVal
            if xVal < 0:
                xVal = 2*pi + xVal

            if varData["xList"][xIndex] is None:
                varData["xList"][xIndex] = xVal
            if varData["xList"][rIndex] is None:
                varData["xList"][rIndex] = rVal

        if (Axes["x"]["enable"] is False and Axes["y"]["enable"] is False
                and Axes["z"]["enable"] is False):
            return

        rotationConstraint = cls(indices, "Rotation")
        varData["fList"].append(rotationConstraint)

    @staticmethod
    def getVariables(f, varData):
        """ Adds unique variables names to the x names list for the solver.
        f: a particular fix constraint
        varData: data of the variables used by the constraints
        """
        for axis in f.Components["Base"]:
            objName = f.Components["Base"][axis]["objName"]
            refName = f.Components["Base"][axis]["refName"]
            if objName not in varData["xNames"]:
                varData["xNames"].append(objName)
            if refName not in varData["xNames"]:
                varData["xNames"].append(refName)
        for axis in f.Components["Rotation"]:
            objName = f.Components["Rotation"][axis]["objName"]
            refName = f.Components["Rotation"][axis]["refName"]
            if objName not in varData["xNames"]:
                varData["xNames"].append(objName)
            if refName not in varData["xNames"]:
                varData["xNames"].append(refName)


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
