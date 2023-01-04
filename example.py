# -*- encoding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import sys

sys.path.append("C:\Users\huber_marc\Desktop\Rhino_Programmierung\lib")
#from baseobjects import Product,Part,Attrib,Feature,SeeleColors,SeeleMaterials
import baseobjects as bo

def GenElements():
    
    job="1770"
    unit="B"
    abruf="Abruf-001"
    bom_extension="txt"
    file_extension="3dm"
    
    folder=r"C:\Users\huber_marc\Desktop\Rhino_Programmierung\project\1770\\"
    
    export=False
    bom=True
    ncdata=True
    
    srfguids=rs.GetObjects("srf",rs.filter.surface)
    srfedges=[[y.EdgeCurve.Rebuild(2,1,False) for y in rs.coercebrep(x).Edges] for x in srfguids]
    srfbound=[Rhino.Geometry.Curve.JoinCurves(x)[0] for x in srfedges]
    #_=[x.Reverse() for x in srfbound]
    srfpts=[[x.Point(j) for j in range(x.PointCount)] for x in srfbound]
    
    rs.EnableRedraw(False)
    
    def EleProto(unit,job,pathqs):
        
        sec=bo.SeeleColors()
        sem=bo.SeeleMaterials(sc)
        
        rawattrib={
        "base":bo.Attrib(job=job,id="",prefix=unit+"4010",zusatztext="-",rawmat="WNXXX",fincode="00",matcode="321",apvorlageno="V-AL35",einkauf="",fertigung="X",auftrag="",lager="X",vbme="m",textpos=False),
        "clip":bo.Attrib(job=job,id="",prefix=unit+"4011",zusatztext="-",rawmat="WNYYY",fincode="00",matcode="321",apvorlageno="V-AL35",einkauf="",fertigung="X",auftrag="",lager="X",vbme="m",textpos=False)}
        rawfeat={
        "base":bo.Feature(name="base",sizex=6000,file=pathqs+"section-1.3dm",layer="base-profile",ro=2700,color=sec("AL"),rhinomat=sem("AL")),
        "clip":bo.Feature(name="clip",sizex=6000,file=pathqs+"section-2.3dm",layer="clip-profile",ro=2700,color=sec("AL"),rhinomat=sem("AL"))}
        
        userdic={
        "base":{"x":38.,"y":47.},
        "clip":{"x":7.1,"y":17.5,"alpha":15.9}
        }
        
        profiles=[]
        for key in rawattrib:
            profiles.append(bo.Profile(attrib=rawattrib[key],feature=rawfeat[key],dic=userdic[key]))
        
        feat=bo.Feature(name="kef-ele")
        attr=bo.Attrib(job=job,id="ele",prefix=unit+"4010",zusatztext="unit-asm",rawmat="",matcode="",apvorlageno="V-AL21",block=True)
        ele=bo.Product(attrib=attr,feature=feat)
        
        efeat=bo.Feature(name="kef-edge")
        eattr=bo.Attrib(job=job,id="",prefix="edge",apvorlageno="- keine AP+ Anlage -",block=False)           
        edge=bo.Product(attrib=eattr,feature=efeat)
        
        for k,_ in enumerate(profiles):
            edge.Profiles.append(profiles[k].Copy())
        
        ele.Products.append(edge)
        
        return ele
    
    headprod=bo.Product(bo.Attrib(apvorlageno="stuelikopf",zusatztext=job+"_BT-B_Abruf-X"),bo.Feature())
    nccollecte=bo.Product(bo.Attrib(apvorlageno="nc-dummy",zusatztext=""),bo.Feature())
    eleproto=EleProto(unit,job,folder)
    
    for i,srfguid in enumerate(srfguids):
        
        name=i
        
        plane=Rhino.Geometry.Plane(srfpts[i][0],srfpts[i][1],srfpts[i][-2])
        element=eleproto.Copy(plane=None,subelements=True)
        
        ac=reduce(lambda x,y:x+y,srfpts[i][:-1])/(len(srfpts[i])-1)
        for j,_ in enumerate(srfpts[i][:-1]):
            vx=srfpts[i][j+1]-srfpts[i][j]
            vx.Unitize()
            pl=Rhino.Geometry.Plane(srfpts[i][j],srfpts[i][j+1],ac)
            pl.Origin+=pl.XAxis*-500
            element.Products.append(element.Products[0].Copy(plane=pl,subelements=True))
            pls=Rhino.Geometry.Plane(srfpts[i][j],vx*-1)
            ple=Rhino.Geometry.Plane(srfpts[i][j+1],vx)
            for k in range(2):
                nccollecte.Profiles.append(element.Products[-1].Profiles[k])
                element.Products[-1].Profiles[k].Attrib.ID="{0:d}-{1:d}".format(name,j)
                element.Products[-1].Profiles[k].Features[0].Plane=pl
                
                element.Products[-1].Profiles[k].ApplyFeatures(
                    tolerance=sc.doc.ModelAbsoluteTolerance,
                    features=[
                        bo.Feature(name="L",nctype=bo.NCTypes().Saw,nccutspace=0,plane=pls),
                        bo.Feature(name="R",nctype=bo.NCTypes().Saw,nccutspace=0,plane=ple)])
            
        element.Products.pop(0)
        element.Features[0].Plane=plane
        
        elbl=element.Show(sc,group=False,block=True,writeattribtoobject=True)
        if export:bo.Export(obj=elbl,filename=element.Attrib.PosNo(),path=folder,format="stp",deleteblock=False)
        headprod.Products.append(element)
        
    if ncdata:
        ncc=nccollecte.ToNCCollection()
        for key in ncc:
            ncc[key].ExportCSV(folder)
        
    if bom:bo.SaveAsciFile(str(headprod.ToAPArtikel()),"{}\{}.{}".format(folder,abruf,bom_extension))
    rs.EnableRedraw(True)

    
    return    
   

if __name__=="__main__":
    GenElements()