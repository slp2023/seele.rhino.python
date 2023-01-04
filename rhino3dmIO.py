import sys
import clr
clr.AddReference("Rhino3dmIO")
import Rhino

import webbrowser as ws

# 2020-03-20 by S.Lippert:
# this module can be used with pure python outside a running rhino instance
# it allows reading and writing of informtion from 3dm files  
# to use Rhino3dmIO.dll (.NET) in pure python clr module needs to be installed as described below

# clr installation via:
# pip install pythonnet
# https://pypi.org/project/pythonnet/
# https://developer.rhino3d.com/guides/opennurbs/what-is-rhino3dmio/
# https://developer.rhino3d.com/api/RhinoCommon/html/T_Rhino_FileIO_File3dm.htm
# https://developer.rhino3d.com/api/rhino3dm

class RhinoFileUtil(object):

    def __init__(self,file):
        try:
            self.File=Rhino.FileIO.File3dm.Read(file)
            self.Objects=[obj for obj in self.File.Objects]
        except:
            self.File=None
            self.Objects=None
            print ("error:",sys.exc_info()[1])
        
        self.RG=Rhino.Geometry
        self.Hyperlink='https://developer.rhino3d.com/api/rhino3dm'
        
    def Info(self):
        ws.open(self.Hyperlink)
        pass

    def GetPoints(self):
        return [obj for obj in self.Objects if isinstance(obj.Geometry,Rhino.Geometry.Point)]

    def GetCurves(self):
        return [obj for obj in self.Objects if isinstance(obj.Geometry,Rhino.Geometry.Curve)]

    def GetLineCurves(self,objs=None):
        if objs==None:
            objs=self.Objects
        return [obj for obj in objs if isinstance(obj.Geometry,Rhino.Geometry.LineCurve)]

    def GetPolylineCurves(self,objs=None):
        if objs==None:
            objs=self.Objects
        return [obj for obj in objs if isinstance(obj.Geometry,Rhino.Geometry.PolylineCurve)]

    def GetMeshes(self):
        return [obj for obj in self.Objects if isinstance(obj.Geometry,Rhino.Geometry.Mesh)]

    def GetBreps(self,objs=None):
        if objs==None:
            objs=self.Objects
        return [obj for obj in objs if isinstance(obj.Geometry,Rhino.Geometry.Brep)]

    def GetBrepRenderMeshes(self,objs=None):
        if objs==None:
            objs=self.Objects
        mesh=[]
        for brep in self.GetBreps(objs):
            for brepface in brep.Geometry.Faces:
                msh=brepface.GetMesh(Rhino.Geometry.MeshType.Render)    
                if msh!=None:
                    mesh.append(msh)
        return mesh

    def GetGroups(self):
        groups=[]
        for x in self.File.AllGroups:
            gm=self.File.AllGroups.GroupMembers(x.Index)
            lc=self.GetLineCurves(gm)
            plc=self.GetPolylineCurves(gm)
            brep=self.GetBreps(gm)
            rmesh=self.GetBrepRenderMeshes(gm)          
            groups.append(CustomGroup(name=x.Name,lines=lc,polylines=plc,breps=brep,meshes=rmesh))

        return groups
    
    def GetObjectsByName(self,objs=None,name=""):
        if objs==None:
            objs=self.Objects
        return [obj for obj in objs if obj.Attributes.Name==name]

class CustomGroup(object):

    def __init__(self,name="",lines=None,polylines=None,breps=None,meshes=None):

        self.Name=name
        self.Lines=lines
        self.Polylines=polylines
        self.Breps=breps
        self.Meshes=meshes




def Test():

    rfu=RhinoFileUtil(r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\lib\rhino3dmIO_testfile.3dm")
    # rfu.Help()
    # return
    if rfu.File!=None:
        print("File contains: {0:d} objects".format(rfu.File.Objects.Count))
    else:
        print("failed to read file...")
    pass

if __name__=="__main__":
    Test()
