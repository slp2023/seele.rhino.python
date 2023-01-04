import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import seeleScriptSyntax as sss
import time

see = sss.seeleScriptSyntax()
tolmod = sc.doc.ActiveDoc.ModelAbsoluteTolerance

def GenHoles_d20mm():
    
    einteilung_lang = 10
    einteilung_kurz = 20
    
    srf = rs.GetObjects("select backpan surface",rs.filter.surface)
    rs.EnableRedraw(False)
    start = time.time()
    for s in srf:
        
        brep_rep = rs.coercebrep(s)
        srf_rep = rs.coercesurface(s)
        
        #generate offset edge curves
        crv_edges = brep_rep.DuplicateEdgeCurves()
        crv_off_list = []
        for crv in  crv_edges:
            crv_off = Rhino.Geometry.Curve.OffsetOnSurface(crv, srf_rep, 50.0, tolmod)[0]
            crv_off_list.append(sc.doc.Objects.Add(crv_off))
        
        #generate trim breps
        split_breps = []
        for i,off in enumerate(crv_off_list):
            parA = rs.CurveCurveIntersection(off,crv_off_list[i-1])[0][5]
            
            if i!=(len(crv_off_list)-1):
                index = i+1
            else:
                index = 0
            
            parB = rs.CurveCurveIntersection(off,crv_off_list[index])[0][5]
            
            crv_split = rs.SplitCurve(off,[parA,parB],False)[1]
            
            #Durchmesser
            if rs.CurveLength(crv_split)>2000:
                val_div = 10
            else:
                val_div = 5
            
            #divide curve and define hole locations 
            pts_div = rs.DivideCurve(crv_split,val_div)
            for pt in pts_div:
                closest_pt = rs.BrepClosestPoint(s,pt)
                plane = rs.PlaneFromNormal(closest_pt[0],closest_pt[3])
                plane.Origin+=plane.Normal*-10
                brep_cyl = Rhino.Geometry.Cylinder(Rhino.Geometry.Circle(plane,10),30).ToBrep(False,False)
                split_breps.append(brep_cyl)
        
        #generate final surface
        brep_split = see.SplitBrepCutters(brep_rep,split_breps,coerce=True)
        
        final_surface = sc.doc.Objects.Add(brep_split[0])
        rs.ObjectColor(final_surface,[0,255,0])
        
        rs.DeleteObjects(rs.ObjectsByType(4))
    end = time.time()
    hours, rem = divmod(end-start, 3600)
    minutes, seconds = divmod(rem, 60)
    print("{:0>2}:{:0>2}:{:05.2f}".format(int(hours),int(minutes),seconds))
    rs.EnableRedraw(True)
    
GenHoles_d20mm()