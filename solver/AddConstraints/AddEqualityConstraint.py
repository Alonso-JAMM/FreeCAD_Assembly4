import os
from PySide import QtGui
import FreeCAD as App
import FreeCADGui as Gui
import libAsm4 as asm4


class EqualityConstraintCmd:
    """ Adds an equality constraint into the assembly"""

    def GetResources(self):
        return {
            "MenuText": "Add equality constraint",
            "ToolTip": "Creates new equality constraint into the assembly",
            "Pixmap": os.path.join(asm4.iconPath, "Draft_Dimension.svg")
        }

    def IsActive(self):
        if App.ActiveDocument:
            return (True)
        else:
            return (False)

    def Activated(self):
        panel = EqualityPanel()
        Gui.Control.showDialog(panel)


class EqualityPanel:
    def __init__(self):
        self.type = "Equality_Constraint"
        self.form = Gui.PySideUic.loadUi(
            os.path.join(
                asm4.wbPath,
                "Resources/ui/TaskPanel_EqualityConstraint.ui"))
        self.addObjects()

    def accept(self):
        obj1 = self.form.firstObjectList.selectedItems()[0].text()
        obj2 = self.form.secondObjectList.selectedItems()[0].text()
        components = {
            "Base": {
                "x": {
                    "enable": False,
                    "obj1Name": obj1 + ".Base.x",
                    "obj2Name": obj2 + ".Base.x",
                },
                "y": {
                    "enable": False,
                    "obj1Name": obj1 + ".Base.y",
                    "obj2Name": obj2 + ".Base.y",
                },
                "z": {
                    "enable": False,
                    "obj1Name": obj1 + ".Base.z",
                    "obj2Name": obj2 + ".Base.z",
                },

            },
            "Rotation": {
                "x": {
                    "enable": False,
                    "obj1Name": obj1 + ".Rotation.x",
                    "obj2Name": obj2 + ".Rotation.x",
                },
                "y": {
                    "enable": False,
                    "obj1Name": obj1 + ".Rotation.y",
                    "obj2Name": obj2 + ".Rotation.y",
                },
                "z": {
                    "enable": False,
                    "obj1Name": obj1 + ".Rotation.z",
                    "obj2Name": obj2 + ".Rotation.z",
                },
            },
        }
        if not obj1 or not obj2:
            print("Select first and second objects")
            return
        if obj1 == obj2:
            print("Select two distinct objects")
            return
        if self.form.xCheck.isChecked():
            # We want to set the x-coordinates of both objects equal
            components["Base"]["x"]["enable"] = True
        if self.form.yCheck.isChecked():
            # we want to set the y-coordinates of both objects equal
            components["Base"]["y"]["enable"] = True
        if self.form.zCheck.isChecked():
            # we want to set the z-coordinates of both objects equal
            components["Base"]["z"]["enable"] = True
        if self.form.xrotCheck.isChecked():
            # Set rotation about x-axis equal
            components["Rotation"]["x"]["enable"] = True
        if self.form.yrotCheck.isChecked():
            # set rotation about y-axis equal
            components["Rotation"]["y"]["enable"] = True
        if self.form.zrotCheck.isChecked():
            # Set rotation about z-axis equal
            components["Rotation"]["z"]["enable"] = True

        newConstraint = App.ActiveDocument.addObject("App::FeaturePython", self.type)
        EqualityConstraint(newConstraint, obj1, obj2, self.type, components)
        Gui.Control.closeDialog()
        App.ActiveDocument.recompute()

    def addObjects(self):
        # Here we populate the list view widgets
        for obj in App.ActiveDocument.Objects:
            if obj.TypeId not in asm4.datumTypes:
                continue
            newItem = QtGui.QListWidgetItem()
            newItem.setText(obj.Name)
            newItem.setIcon(obj.ViewObject.Icon)
            self.form.firstObjectList.addItem(newItem)
        for obj in App.ActiveDocument.Objects:
            if obj.TypeId not in asm4.datumTypes:
                continue
            newItem = QtGui.QListWidgetItem()
            newItem.setText(asm4.nameLabel(obj))
            newItem.setIcon(obj.ViewObject.Icon)
            self.form.secondObjectList.addItem(newItem)


class EqualityConstraint():
    def __init__(self, obj, obj1, obj2, constraintType, components):
        obj.Proxy = self
        obj.addProperty("App::PropertyString", "Type", "", "", 1)
        obj.Type = constraintType
        obj.addProperty("App::PropertyString", "Object_1")
        obj.Object_1 = obj1
        obj.addProperty("App::PropertyString", "Object_2")
        obj.Object_2 = obj2
        obj.addProperty("App::PropertyBool", "Base_x", "Placement")
        obj.addProperty("App::PropertyBool", "Base_y", "Placement")
        obj.addProperty("App::PropertyBool", "Base_z", "Placement")
        obj.addProperty("App::PropertyBool", "Rotation_x", "Placement")
        obj.addProperty("App::PropertyBool", "Rotation_y", "Placement")
        obj.addProperty("App::PropertyBool", "Rotation_z", "Placement")
        obj.addProperty("App::PropertyPythonObject", "Components", "", "", 4)
        obj.Components = components
        for compType in components:
            for compAxis in components[compType]:
                if not components[compType][compAxis]["enable"]:
                    continue
                # Name of the property to put the value
                prop = compType + "_" + compAxis
                setattr(obj, prop, True)    # Enable this constraint
        App.ActiveDocument.Constraints.addObject(obj)

    def onChanged(self, obj, prop):
        """ Callback for propeties changed. It checks which placement
        components have changed and updates the components list when needed
        """
        if prop == "Base_x":
            self.changeComponent(obj, prop, "Base_x")
        elif prop == "Base_y":
            self.changeComponent(obj, prop, "Base_y")
        elif prop == "Base_z":
            self.changeComponent(obj, prop, "Base_z")
        elif prop == "Rot_x":
            self.changeComponent(obj, prop, "Rotation_x")
        elif prop == "Rot_y":
            self.changeComponent(obj, prop, "Rotation_y")
        elif prop == "Rot_z":
            self.changeComponent(obj, prop, "Rotation_z")

    @staticmethod
    def changeComponent(obj, prop, component):
        """ Function that modifies the equality constriant components list when
        one of the component booleans is modified in the property editor. That
        is, when the user adds or deletes an equality constraint to some
        placement component in the property editor.
        obj: the featurepython object of the equality constraint.
        prop: the property of obj being changed.
        component: the component we are interested. For example ".Base.x"
        component will be used to form each variable so its format is important
        """
        propType = prop.split("_")[0]
        propAxis = prop.split("_")[1]
        # When loading the document the object properties are touched;
        # however, not all the properties are loaded yet which gives 
        # errors related to the object not having a property. So we
        # do nothing if the valueProp has not being loaded yet.
        # The information about the fix constraint value is already
        # in the dictionary when loading the object.
        if obj.Components[propType][propAxis]["enable"]:
            if not getattr(obj, prop):
                obj.Components[propType][propAxis]["enable"] = False
        else:
            if getattr(obj, prop):
                obj.Components[propType][propAxis]["enable"] = True


Gui.addCommand("Asm4_EqualityConstraint", EqualityConstraintCmd())
