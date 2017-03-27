# A Modified Version of the Douglas-Peucker Algorithm for Vertex Weeding According to Z-Values
# From 3.14 Chiyuan Gu& Furui Sun
# FID FID_test_b POINT_Z
# Imports
# -------
import arcpy
import os
import string
import math
import sys
from operator import itemgetter
from arcpy import env

# Functions
# ---------
# get the transferred x coordinates:distance between points on the same line
def _gettransferx(pnts,p0):
	dist = []
	for ix in range(len(pnts)):
		pnt0 = pnts[p0]
		pnt1 = pnts[ix]
		d = math.sqrt( (pnt1[0]-pnt0[0]) * (pnt1[0]-pnt0[0])+ (pnt1[1]-pnt0[1]) * (pnt1[1]-pnt0[1]))
		dist.append(d)
	return dist

# get the perpendicular distance from the point to the line
def _perpendicular_distance(xn,yn,xm,ym,x,y):
	L=math.sqrt((ym-yn)*(ym-yn)+(xm-xn)*(xm-xn))
	A=(ym-yn)/L
	B=(xn-xm)/L
	C=(xm*yn-xn*ym)/L
	d=math.fabs(A*x+B*y+C)
	return d

# use douglas-Peucker algrithom to simplify the data 
# pnts is the array of points on the same line
def _douglaspeucker(pnts,tolerance):
	max=0.0
	t=0
	for k in range(1, len(pnts)-1):
		dis=_perpendicular_distance(pnts[0][0],pnts[0][1],pnts[-1][0],pnts[-1][1],pnts[k][0],pnts[k][1])
		if dis>max:
			max=dis
			t=k
	if max>tolerance:
		results=_douglaspeucker((pnts[:t+1])[:-1],tolerance)+_douglaspeucker(pnts[t:],tolerance)
	else: 
		results = [pnts[0], pnts[-1]]
	return results

# add a field called "MARKER" in the attribute table which helps us mark the reserved points 
def _checkrecordsinfor(inFC,pnts_id,n):
	fieldList = ["FID", "MARKER"]
	cursor = arcpy.UpdateCursor(inFC,fieldList)
	for row in cursor:
		for ix in range(n):
			if row.getValue(fieldList[0]) == resulted_pnts_id[ix]:
				row.setValue(fieldList[-1],1)
				cursor.updateRow(row)
	del cursor
	
# Set overwrite option
# --------------------
arcpy.env.overwriteOutput = True        

# Definition of inputs
# --------------------
# Set environment settings

# with open("E:/Project/Shape/intersections.shp") as f:
	# for line in f:
		# drive,path = os.path.splitdrive(line)
		# path,filename = os.path.split(path)
		# print('Drive is %s Path is %s and file is %s' % (drive, path, filename))
		
# env.workspace = arcpy.GetParameterAsText(1)
inFC = arcpy.GetParameterAsText(0)
tmpFCName = "temp.shp"

#outputshapefile
outLocation=arcpy.GetParameterAsText(2)
outFeatureClass = arcpy.GetParameter(3)
outFC = arcpy.GetParameterAsText(2)+ "\\"+arcpy.GetParameter(3)

tolerance = arcpy.GetParameter(1)
rows = arcpy.SearchCursor(inFC)
eachline=[]
point_x=[]
point_y=[]
point_z=[]
id=[]
line=[]
line_num=[]
x_t=[]
y_t=[]
xy_t=[]
result=[]
pnts_id=[]
resulted_pnts_id=[]

#read the field data from shapefile
for row in rows:
	line.append(row.getValue('FID_test_b'))
	point_x.append(row.getValue('POINT_X'))
	point_y.append(row.getValue('POINT_Y'))
	point_z.append(row.getValue('POINT_Z'))
	id.append(row.getValue('FID'))
line_num=list(set(line)) #get the number of lines of polygons

for t in range(len(line_num)):
	for i in range(len(line)):
		if line[i] == line_num[t]:
			eachline.append([point_x[i],point_y[i],point_z[i],id[i]])# put points on the same line in a list called eachline
	k=abs((eachline[1][1]-eachline[0][1])/(eachline[1][0]-eachline[0][0]))
	# if the line tend to be horizontal(based on its slope), select the point with the minimum x coordinate to be the original point(as the base point to calculate the distance between points)
	if k < 1:
		xmin_index=eachline.index(min(eachline))
		# assign distance to be the transferred x-coordinate
		x_t=_gettransferx(eachline,xmin_index)
		# assign the z value(elevation) to be as the transferred y-coordinate
		for n in range(len(eachline)):
			xy_t.append([x_t[n],eachline[n][2],eachline[n][3]])
		xy_t_sorted=sorted(xy_t,key=itemgetter(0)) # order the points 
		result=_douglaspeucker(xy_t,tolerance)
		x_t[:] = []
		xy_t[:] = []
	# if the line tend to be vertical(based on its slope), select the point with the minimum y coordinate to be the original point(as the base point to calculate the distance between points)
	else:
		ymin=eachline[0][1]
		# to find the minimum y-coordinate of the point on the same line
		for ii in range(len(eachline)):
			if eachline[ii][1]<ymin:
				ymin=eachline[ii][1]
				ymin_index=ii
		# assign distance to be the transferred x-coordinate
		x_t=_gettransferx(eachline,ymin_index)
		# assign the z value(elevation) to be as the transferred y-coordinate
		for n in range(len(eachline)):
			xy_t.append([x_t[n],eachline[n][2],eachline[n][3]])
		xy_t_sorted=sorted(xy_t,key=itemgetter(0))# order the points
		result=_douglaspeucker(xy_t,tolerance)
		x_t[:] = []
		xy_t[:] = []
	pnts_id.append(zip(*result)[2])#get the ids of reserved points
	eachline[:] = []
	
resulted_pnts_id=sum(pnts_id, ()) #flatten the tuple of list

# create a new field for marker
arcpy.AddField_management (inFC,"MARKER", "FLOAT")
# get the number of points that will be maintained
pnumber = len(resulted_pnts_id)
#check and mark those points that should be maintained
_checkrecordsinfor(inFC,resulted_pnts_id,pnumber)

# Execute FeatureClassToFeatureClass
arcpy.FeatureClassToFeatureClass_conversion(inFC,outLocation,outFeatureClass)

# create a feature layer and perform a selection to select unreserved points
arcpy.MakeFeatureLayer_management(outFC, "Temp")
whereClause = ' "MARKER" = 0 '
arcpy.SelectLayerByAttribute_management("Temp", "NEW_SELECTION", whereClause)

# delete all selected features
arcpy.AddMessage("--- Reduction to redundant features")
arcpy.DeleteFeatures_management ("Temp")
# delete MARKER field from original input feature shapefile
arcpy.DeleteField_management(inFC,"MARKER")

arcpy.AddMessage("--- Job completed")

