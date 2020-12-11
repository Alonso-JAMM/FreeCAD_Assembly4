#!/usr/bin/env python3
# coding: utf-8
# 
# updateAssembly.py 


import time
import math, re, os
import numpy as np

from PySide import QtGui, QtCore
import FreeCADGui as Gui
import FreeCAD as App
import Part

import libAsm4 as Asm4

from math import pi
from solver.Solver import Solver
from solver.Solver import get_lists
from solver.HyperDual import HyperDualQuaternion
from solver.HyperDual import hdcos
from solver.HyperDual import hdsin


class updateAssembly:

    def GetResources(self):
        return {"MenuText": "Solve and Update Assembly",
                "ToolTip": "Update Assembly",
                "Pixmap" : os.path.join( Asm4.iconPath , 'Asm4_Solver.svg')
                }


    def IsActive(self):
        if App.ActiveDocument:
            return(True)
        return(False)


    """
    +-----------------------------------------------+
    |                 the real stuff                |
    +-----------------------------------------------+
    """
    def Activated(self):
        # find every Part in the document ...
        for obj in App.ActiveDocument.Objects:
            # ... and update it
            if obj.TypeId == 'App::Part':
                obj.recompute('True')
        #App.ActiveDocument.recompute()
        # Check if there is a model in the Document before solving constraints
        if Asm4.checkModel() is None:
            return
        t = time.time()
        varData = get_lists()
        # === Attempt for general Solver ===
        fList = varData["fList"]
        xHD = varData["xHD"]
        xi = np.zeros_like(xHD)
        for i in range(len(xHD)):
            xi[i] = xHD[i].real
        sol = Solver(xHD, fList)
        solved = sol.solve(xi)

        objRotations = {}
        for i in range(len(xHD)):
            obj = varData["xNames"][i]
            obj_name = obj.split(".")[0]
            component = obj.split(".")[2]
            placement = obj.split(".")[1]
            if placement == "Rotation":
                if obj_name not in objRotations:
                    objRotations[obj_name] = {"x": 0, "y": 0, "z": 0}
                angles = App.ActiveDocument.getObject(obj_name).Placement.Rotation.toEuler()
                if component == "x":
                    objRotations[obj_name]["x"] = solved.x[i]*180/pi
                    App.ActiveDocument.getObject(obj_name).Placement.Rotation = App.Rotation(angles[0], angles[1], solved.x[i]*180/pi)
                elif component == "y":
                    objRotations[obj_name]["y"] = solved.x[i]*180/pi
                    App.ActiveDocument.getObject(obj_name).Placement.Rotation = App.Rotation(angles[0], solved.x[i]*180/pi, angles[2])
                elif component == "z":
                    objRotations[obj_name]["z"] = solved.x[i]*180/pi
                    App.ActiveDocument.getObject(obj_name).Placement.Rotation = App.Rotation(solved.x[i]*180/pi, angles[1], angles[2])
            elif placement == "Base":
                if component == "x":
                    App.ActiveDocument.getObject(obj_name).Placement.Base.x = solved.x[i]
                elif component == "y":
                    App.ActiveDocument.getObject(obj_name).Placement.Base.y = solved.x[i]
                elif component == "z":
                    App.ActiveDocument.getObject(obj_name).Placement.Base.z = solved.x[i]
#        for objName in objRotations:
        timeUsed = time.time() - t
#        print(solved.x)
#        print(f"solver took {timeUsed}")
        return


# add the command to the workbench
Gui.addCommand( 'Asm4_updateAssembly', updateAssembly() )
