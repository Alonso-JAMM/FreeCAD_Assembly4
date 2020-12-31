from scipy.optimize import minimize
import numpy as np
import FreeCAD as App
from .HyperDual import HyperDual, HyperDualQuaternion, hdsin, hdcos
from .Constraints import Equality, Fix, Lock


class Solver:
    def __init__(self, x=None, f=None, varData=None):
        self.x = x              # List  of variables to be solved (hyper duals)
        self.f = f              # List of constraint objects
        self.val = None         # Value of function at current point
        self.current_x = None   # Current point
        self.varData = varData

    def eval(self, x):
        """ Evaluate the sum of squares used by the minimize function"""
        for i in range(x.shape[0]):
            self.x[i].real = x[i]

        updatePlacements(self.varData)

        total = HyperDual(0, 0, 0)
        for i in range(len(self.f)):
            if self.f[i].Ftype == "Fix":
                if self.f[i].fixType == "Base":
                    result = self.f[i].eval(self.x)
                    total += result  # .q1**2 + result.q2**2 + result.q3**2
                else:
                    result = self.f[i].eval(self.x)
                    total += result.q0**2 + result.q1**2 + result.q2**2
            else:
                total += self.f[i].eval(self.x)**2

        self.val = total
        self.current_x = x
        return self.val.real

    def grad(self, x):
        """ Returns teh gradient of evaluated sum of squares """
        # Checks that we have evaluated the fuction at point x
        if not np.array_equal(self.current_x, x):
            self.eval(x)
        return self.val.grad

    def hess(self, x):
        """ Returns the hessian of evaluated sum of squares """
        # Checks that we have evaluated the function at point x
        if not np.array_equal(self.current_x, x):
            self.eval(x)
        return self.val.hess

    def solve(self, initial_x=None, constraints=None):
        """ Tries to solve the sum of squares problem.
            initial_x: list of initial values for the solver (list of reals)
            constraints: list of constraint objects """
        # if initial_x:
        #    self.x = convert_to_hp(initial_x)

        # if constraints:
        #    self.f = constraints

        x0 = np.array(initial_x, dtype=np.float)
        solution = minimize(self.eval, x0,  method="trust-ncg",
                            jac=self.grad, hess=self.hess,
                            options={"gtol": 1e-8, "disp": True})
        return solution

    def convert_to_hp(self, real_list):
        """ Convert numbers in real list to a list of hyperduals """
        n = len(real_list)
        hd_list = []

        for i in range(len(real_list)):
            hd_list.append()


def get_lists():
    """
    Gets the variables names and values as well as the functions
    representing the constraints of the assembly.
    Returns a dictionary containing 4 lists.
    fList: contains the constraint functions.
    xList: contains the current values of the variables.
    xHD: contains the current values of the variables in
    hyperdual form.
    variables: containes all the variables in the system
    placements: contains the base position and the rotations corresponding
    to all the objects inside the system. They are built from the variables
    freeVarCount: contains the number of variables that are not locked. These
    variables will be used by the optimization algorithm.
    """
    # varData stores the variables names and values and the
    # constraints functions
    varData = {
        "fList": [],
        "xList": [],
        "xHD": [],     # list of hyper duals
        "variables": {},  # New variable container
        "placements": {},  # placements of objects constructed from variables
        "freeVarCount": 0,  # Number of variables
    }

    # begin by finding the variables
    for f in App.ActiveDocument.Constraints.Group:
        if f.Type == "Equality_Constraint":
            Equality.getVariables(f, varData)
        elif f.Type == "Fix_Constraint":
            Fix.getVariables(f, varData)
        elif f.Type == "Lock_Constraint":
            Lock.getVariables(f, varData)

    # Now we count the number of free variablesa
    i = 0
    for variable in varData["variables"]:
        if (not varData["variables"][variable]["locked"] and
                varData["variables"][variable]["equal"] is None):
            varData["variables"][variable]["index"] = i
            i += 1
    varData["freeVarCount"] = i

    # Then get the current variables values
    n = varData["freeVarCount"]
    varData["xList"] = [None]*n
    for f in App.ActiveDocument.Constraints.Group:
        if f.Type == "Fix_Constraint":
            Fix.makeConstraintBase(f, varData)
            Fix.makeConstraintRotation(f, varData)

    # Build the hyper dual number for base and rotation placements
    i = 0
    initialHess = np.zeros((n, n))
    for variable in varData["variables"]:
        x = varData["variables"][variable]["currentValue"]
        if varData["variables"][variable]["locked"]:
            varData["variables"][variable]["value"] = x
            continue
        if varData["variables"][variable]["equal"] is not None:
            continue
        newGrad = np.zeros(n)
        newGrad[i] = 1
        newHD = HyperDual(x, newGrad, initialHess)
        varData["variables"][variable]["value"] = newHD
        varData["xHD"].append(newHD)
        i += 1

    # Now we make sure the equality constraints are satisfied
    for variable in varData["variables"]:
        if varData["variables"][variable]["equal"] is None:
            continue
        refName = varData["variables"][variable]["equal"]
        x = varData["variables"][refName]["value"]
        varData["variables"][variable]["value"] = x

    return varData


def updatePlacements(varData):
    """
    Updates the placements in varData using the variables stored here.
    This way, the constraint objects don't have to recalculate the same
    numbers all the time.
    """
    # We first set up the rotations about the axes
    for variable in varData["variables"]:
        if varData["variables"][variable]["equal"] is not None:
            continue
        if "Rotation" not in variable:
            continue
        angle = varData["variables"][variable]["value"]
        axis = variable.split(".")[2]
        q = None
        if axis == "x":
            q = HyperDualQuaternion(hdsin(angle*0.5),
                                    0,
                                    0,
                                    hdcos(angle*0.5))
        elif axis == "y":
            q = HyperDualQuaternion(0,
                                    hdsin(angle*0.5),
                                    0,
                                    hdcos(angle*0.5))
        elif axis == "z":
            q = HyperDualQuaternion(0,
                                    0,
                                    hdsin(angle*0.5),
                                    hdcos(angle*0.5))

        varData["variables"][variable]["q"] = q
    for pla in varData["placements"]:
        if varData["variables"][variable]["equal"] is not None:
            continue
        # Construct the base placements
        if "Base" in pla:
            xName = pla + ".x"
            yName = pla + ".y"
            zName = pla + ".z"
            xValue = varData["variables"][xName]["value"]
            yValue = varData["variables"][yName]["value"]
            zValue = varData["variables"][zName]["value"]
            varData["placements"][pla] = HyperDualQuaternion(xValue, yValue, zValue, 0)
        elif "Rotation" in pla:
            xName = pla + ".x"
            yName = pla + ".y"
            zName = pla + ".z"
            xVal = varData["variables"][xName]["q"]
            yVal = varData["variables"][yName]["q"]
            zVal = varData["variables"][zName]["q"]
            # Assuming we already converted angles to quaternions
            varData["placements"][pla] = zVal@yVal@xVal
