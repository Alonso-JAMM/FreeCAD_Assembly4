import os
import libAsm4 as asm4
from PySide import QtGui
import FreeCAD as App
import FreeCADGui as Gui


class LockConstraintCmd:

    def GetResources(self):
        return {
            "MenuText": "Add Lock constraint",
            "ToolTip": "Creates new Lock constraint into the assembly",
            "Pixmap": os.path.join(asm4.iconPath, "Draft_Dimension.svg")
        }

    def IsActive(self):
        if App.ActiveDocument:
            return(True)
        else:
            return(False)

    def Activated(self):
        panel = LockPanel()
        Gui.Control.showDialog(panel)


class LockPanel:
    def __init__(self):
        self.type = "Lock_Constraint"
        self.form = Gui.PySideUic.loadUi(
            os.path.join(
                asm4.wbPath,
                "Resources/ui/TaskPanel_LockConstraint.ui"))
        self.addObjects()

    def accept(self):
        objName = self.form.objectList.selectedItems()[0].text()
        qty = App.Units.Quantity
        components = {
            "Base_x": {
                "value": 0,
                "enable": False,
                "objName": objName + ".Base.x",
            },
            "Base_y": {
                "value": 0,
                "enable": False,
                "objName": objName + ".Base.y",
            },
            "Base_z": {
                "value": 0,
                "enable": False,
                "objName": objName + ".Base.z",
            },
            "Rotation_x": {
                "value": 0,
                "enable": False,
                "objName": objName + ".Rotation.x",
            },
            "Rotation_y": {
                "value": 0,
                "enable": False,
                "objName": objName + ".Rotation.y",
            },
            "Rotation_z": {
                "value": 0,
                "enable": False,
                "objName": objName + ".Rotation.z",
            }
        }
        if not objName:
            print("Select an object first")
            return
        if self.form.xCheck.isChecked():
            # Fix x coordinate of object
            value = qty(self.form.xVal.text()).Value
            components["Base_x"]["value"] = value
            components["Base_x"]["enable"] = True
        if self.form.yCheck.isChecked():
            # Fix y coordinate of object
            value = qty(self.form.yVal.text()).Value
            components["Base_y"]["value"] = value
            components["Base_y"]["enable"] = True
        if self.form.zCheck.isChecked():
            # Fix z coordinate of object
            value = qty(self.form.zVal.text()).Value
            components["Base_z"]["value"] = value
            components["Base_z"]["enable"] = True
        if self.form.xrotCheck.isChecked():
            # fix rotation about x axis
            value = qty(self.form.xrotVal.text()).Value
            components["Rotation_x"]["value"] = value
            components["Rotation_x"]["enable"] = True
        if self.form.yrotCheck.isChecked():
            # fix rotation about y axis
            value = qty(self.form.yrotVal.text()).Value
            components["Rotation_y"]["value"] = value
            components["Rotation_y"]["enable"] = True
        if self.form.zrotCheck.isChecked():
            # Fix rotation about z axis
            value = qty(self.form.zrotVal.text()).Value
            components["Rotation_z"]["value"] = value
            components["Rotation_z"]["enable"] = True

        newConstraint = App.ActiveDocument.addObject("App::FeaturePython", self.type)
        LockConstraint(newConstraint, objName, self.type, components)
        Gui.Control.closeDialog()
        App.ActiveDocument.recompute()

    def addObjects(self):
        for obj in App.ActiveDocument.Objects:
            if obj.TypeId not in asm4.datumTypes:
                continue
            newItem = QtGui.QListWidgetItem()
            newItem.setText(obj.Name)
            newItem.setIcon(obj.ViewObject.Icon)
            self.form.objectList.addItem(newItem)


class LockConstraint:
    def __init__(self, obj, objName, constraintType, components):
        obj.Proxy = self
        obj.addProperty("App::PropertyString", "Type", "", "", 1)
        obj.Type = constraintType
        obj.addProperty("App::PropertyString", "Object")
        obj.Object = objName
        obj.addProperty("App::PropertyString", "Reference")
        obj.addProperty("App::PropertyBool", "Base_x", "Placement")
        obj.addProperty("App::PropertyFloat", "Base_x_val", "Placement")
        obj.addProperty("App::PropertyBool", "Base_y", "Placement")
        obj.addProperty("App::PropertyFloat", "Base_y_val", "Placement")
        obj.addProperty("App::PropertyBool", "Base_z", "Placement")
        obj.addProperty("App::PropertyFloat", "Base_z_val", "Placement")
        obj.addProperty("App::PropertyBool", "Rotation_x", "Placement")
        obj.addProperty("App::PropertyFloat", "Rotation_x_val", "Placement")
        obj.addProperty("App::PropertyBool", "Rotation_y", "Placement")
        obj.addProperty("App::PropertyFloat", "Rotation_y_val", "Placement")
        obj.addProperty("App::PropertyBool", "Rotation_z", "Placement")
        obj.addProperty("App::PropertyFloat", "Rotation_z_val", "Placement")
        obj.addProperty("App::PropertyPythonObject", "Components", "", "", 4)
        obj.Components = components
        for component in components:
            if not components[component]["enable"]:
                continue
            val = components[component]["value"]
            # Name of the property to put the value
            valueProp = component + "_val"
            setattr(obj, valueProp, val)     # Set the fix value of this constraint
            setattr(obj, component, True)    # Enable this constraint
        App.ActiveDocument.Constraints.addObject(obj)

    def onChanged(self, obj, prop):
        if prop in ("Base_x", "Base_x_val"):
            self.changeComponent(obj, "Base_x")
        if prop in ("Base_y", "Base_y_val"):
            self.changeComponent(obj, "Base_y")
        if prop in ("Base_z", "Base_z_val"):
            self.changeComponent(obj, "Base_z")
        if prop in ("Rotation_x", "Rotation_x_val"):
            self.changeComponent(obj, "Rotation_x")
        if prop in ("Rotation_y", "Rotation_y_val"):
            self.changeComponent(obj, "Rotation_y")
        if prop in ("Rotation_z", "Rotation_z_val"):
            self.changeComponent(obj, "Rotation_z")

    @staticmethod
    def changeComponent(obj, prop):
        valueProp = prop + "_val"
        # When loading the document the object properties are touched;
        # however, not all the properties are loaded yet which gives 
        # errors related to the object not having a property. So we
        # do nothing if the valueProp has not being loaded yet.
        # The information about the fix constraint value is already
        # in the dictionary when loading the object.
        if not hasattr(obj, valueProp):
            return
        val = getattr(obj, valueProp)
        if obj.Components[prop]["enable"]:
            if not getattr(obj, prop):
                obj.Components[prop]["enable"] = False
        else:
            if getattr(obj, prop):
                obj.Components[prop]["enable"] = True
        obj.Components[prop]["value"] = val


Gui.addCommand("Asm4_LockConstraint", LockConstraintCmd())
