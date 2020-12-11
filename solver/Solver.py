from scipy.optimize import minimize
import numpy as np
import FreeCAD as App
from .HyperDual import HyperDual
from .Constraints import Equality, Fix, Lock


class Solver:
    def __init__(self, x=None, f=None):
        self.x = x              # List  of variables to be solved (hyper duals)
        self.f = f              # List of constraint objects
        self.val = None         # Value of function at current point
        self.current_x = None   # Current point

    def eval(self, x):
        """ Evaluate the sum of squares used by the minimize function"""
        for i in range(x.shape[0]):
            self.x[i].real = x[i]

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

        x0 = np.array(initial_x)
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
    xNames: contains the names of the variables.
    xList: contains the current values of the variables.
    xHD: contains the current values of the variables in
    hyperdual form.
    """
    # varData stores the variables names and values and the
    # constraints functions
    varData = {
        "fList": [],
        "xNames": [],
        "xList": [],
        "xHD": [],     # list of hyper duals
    }

    # begin by finding the variables
    for f in App.ActiveDocument.Constraints.Group:
        if f.Type == "Equality_Constraint":
            Equality.getVariables(f, varData)
        elif f.Type == "Fix_Constraint":
            Fix.getVariables(f, varData)
        elif f.Type == "Lock_Constraint":
            Lock.getVariables(f, varData)

    # Then get the current variables values
    n = len(varData["xNames"])
    varData["xList"] = [None]*n
    for f in App.ActiveDocument.Constraints.Group:
        if f.Type == "Equality_Constraint":
            Equality.makeConstraint(f, varData)
        if f.Type == "Fix_Constraint":
            Fix.makeConstraintBase(f, varData)
            Fix.makeConstraintRotation(f, varData)
        if f.Type == "Lock_Constraint":
            Lock.makeConstraint(f, varData)

    # Build the hyper dual number for base and rotation placements
    initialHess = np.zeros((n, n))
    i = 0
    for x in varData["xList"]:
        newGrad = np.zeros(n)
        newGrad[i] = 1
        newHD = HyperDual(x, newGrad, initialHess)
        varData["xHD"].append(newHD)
        i += 1
    return varData
