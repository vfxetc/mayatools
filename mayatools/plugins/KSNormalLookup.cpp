#include <math.h>

#include <maya/MDataBlock.h>
#include <maya/MDataHandle.h>
#include <maya/MFloatVector.h>
#include <maya/MPointArray.h>
#include <maya/MFnUnitAttribute.h>
#include <maya/MFnMessageAttribute.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MFnPlugin.h>
#include <maya/MPlug.h>
#include <maya/MPlugArray.h>
#include <maya/MPxNode.h>
#include <maya/MFnMesh.h>
#include <maya/MItMeshPolygon.h>
#include <maya/MGlobal.h>
#include <maya/MString.h>
#include <maya/MTime.h>

#include <glm/glm.hpp>

#include "normal_raster/rendercontext.h"

#ifdef KSNORMAL_DEBUG

#include <iostream>
#include <fstream>

#endif

class KSNormalLookup : public MPxNode
{
	public:
                  KSNormalLookup();
	virtual       ~KSNormalLookup();

	virtual MStatus compute( const MPlug&, MDataBlock& );
	virtual void    postConstructor();

	static  void *  creator();
	static  MStatus initialize();

	static  MTypeId id;

	private:
    static MObject shapeMessageAttr;
    static MObject cameraLocationAttr;
    static MObject lookupPointAttr;
    static MObject cachSizeAttr;
    static MObject lookupUVAttr;
    static MObject timeAttr;
    static MObject outNormalAttr;
    static MObject outFacingRatioAttr;

    NormalRaster::RenderContext m_normal_raster;
    int m_prev_cache_size;
    float m_prev_time;
};

MTypeId KSNormalLookup::id('KSNL');


MObject KSNormalLookup::shapeMessageAttr;
MObject KSNormalLookup::cameraLocationAttr;
MObject KSNormalLookup::lookupPointAttr;
MObject KSNormalLookup::cachSizeAttr;
MObject KSNormalLookup::lookupUVAttr;
MObject KSNormalLookup::timeAttr;
MObject KSNormalLookup::outNormalAttr;
MObject KSNormalLookup::outFacingRatioAttr;


void KSNormalLookup::postConstructor()
{
	setMPSafe(true);
}


KSNormalLookup::KSNormalLookup() : m_prev_cache_size(-1), m_prev_time(0)
{
}


KSNormalLookup::~KSNormalLookup()
{
}


void* KSNormalLookup::creator()
{
    return new KSNormalLookup();
}



MStatus KSNormalLookup::initialize()
{
    MStatus status;
    MFnNumericAttribute nAttr; 
    MFnTypedAttribute tAttr;
    MFnMessageAttribute mAttr;
    MFnUnitAttribute uAttr;

    // This one has a special name that is filled by the sampler.
    lookupPointAttr = nAttr.createPoint("pointWorld", "pw", &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(nAttr.setStorable(false));
    CHECK_MSTATUS(nAttr.setHidden(true));

    // Implicit shading network attributes
    MObject child1 = nAttr.create("uCoord", "u", MFnNumericData::kFloat);
    MObject child2 = nAttr.create("vCoord", "v", MFnNumericData::kFloat);
    lookupUVAttr = nAttr.create("uvCoord", "uv", child1, child2);
    CHECK_MSTATUS(nAttr.setKeyable(true));
    CHECK_MSTATUS(nAttr.setStorable(false));
    CHECK_MSTATUS(nAttr.setReadable(true));
    CHECK_MSTATUS(nAttr.setWritable(true));
    CHECK_MSTATUS(nAttr.setHidden(true));

    timeAttr = uAttr.create( "time", "tm", MFnUnitAttribute::kTime, 0.0, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(uAttr.setKeyable(true));
    CHECK_MSTATUS(uAttr.setStorable(false));
    CHECK_MSTATUS(uAttr.setReadable(true));
    CHECK_MSTATUS(uAttr.setWritable(true));
    //CHECK_MSTATUS(uAttr.setHidden(true));

    shapeMessageAttr = mAttr.create("shapeMessage", "rn", &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(mAttr.setStorable(false));

    cameraLocationAttr = nAttr.createPoint("cameraLocation", "cl", &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(nAttr.setStorable(false));

    cachSizeAttr = nAttr.create("cachSize", "sz", MFnNumericData::kInt, 1024, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(nAttr.setStorable(false));
    CHECK_MSTATUS(nAttr.setMin(0));

    outNormalAttr = nAttr.createColor("outNormal", "on", &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(nAttr.setStorable(false));
    CHECK_MSTATUS(nAttr.setWritable(false));

    outFacingRatioAttr = nAttr.create("outFacingRatio", "or", MFnNumericData::kFloat);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(nAttr.setStorable(false));
    CHECK_MSTATUS(nAttr.setWritable(false));

    CHECK_MSTATUS(addAttribute(shapeMessageAttr));
    CHECK_MSTATUS(addAttribute(cameraLocationAttr));
    CHECK_MSTATUS(addAttribute(cachSizeAttr));
    CHECK_MSTATUS(addAttribute(lookupPointAttr));
    CHECK_MSTATUS(addAttribute(lookupUVAttr));
    CHECK_MSTATUS(addAttribute(timeAttr));
    CHECK_MSTATUS(addAttribute(outNormalAttr));
    CHECK_MSTATUS(addAttribute(outFacingRatioAttr));

    CHECK_MSTATUS(attributeAffects(shapeMessageAttr, outNormalAttr));
    CHECK_MSTATUS(attributeAffects(lookupPointAttr, outNormalAttr));
    CHECK_MSTATUS(attributeAffects(lookupUVAttr, outNormalAttr));
    CHECK_MSTATUS(attributeAffects(cachSizeAttr, outNormalAttr));
    CHECK_MSTATUS(attributeAffects(timeAttr, outNormalAttr));

    CHECK_MSTATUS(attributeAffects(shapeMessageAttr, outFacingRatioAttr));
    CHECK_MSTATUS(attributeAffects(cameraLocationAttr, outFacingRatioAttr));
    CHECK_MSTATUS(attributeAffects(lookupPointAttr, outFacingRatioAttr));
    CHECK_MSTATUS(attributeAffects(lookupUVAttr, outFacingRatioAttr));
    CHECK_MSTATUS(attributeAffects(cachSizeAttr, outFacingRatioAttr));
    CHECK_MSTATUS(attributeAffects(timeAttr, outFacingRatioAttr));

    return MS::kSuccess;
}

static MIntArray GetLocalIndex( MIntArray & getVertices, MIntArray & getTriangle )
{
  MIntArray   localIndex;
  unsigned    gv, gt;

  assert ( getTriangle.length() == 3 );    // Should always deal with a triangle

  for ( gt = 0; gt < getTriangle.length(); gt++ ) {
    for ( gv = 0; gv < getVertices.length(); gv++ ) {
      if ( getTriangle[gt] == getVertices[gv] ) {
        localIndex.append( gv );
        break;
      }
    }

    // if nothing was added, add default "no match"
    if ( localIndex.length() == gt )
      localIndex.append( -1 );
  }

  return localIndex;
}

static void get_normals(const MObject& obj, NormalRaster::RenderContext &ctx)
{
    MStatus status = MS::kSuccess;
    const MFnMesh meshFn(obj);
    MStringArray  UVSets;
    status = meshFn.getUVSetNames( UVSets );

    if (status != MS::kSuccess || !UVSets.length()) {
        MGlobal::displayWarning("no uvsets");
        return;
    }

    MFloatArray   u, v;
    meshFn.getUVs( u, v, &UVSets[0] );

    MFloatVectorArray  meshNormals;
    status = meshFn.getNormals(meshNormals);

    if (status != MS::kSuccess || !meshNormals.length()) {
        MGlobal::displayWarning("no normals");
        return;
    }

    MItMeshPolygon itPolygon(obj);

    for (/*nothing*/; !itPolygon.isDone(); itPolygon.next())
    {
        MIntArray polygonVertices;
        int numTriangles;
        itPolygon.getVertices(polygonVertices);

        CHECK_MSTATUS(itPolygon.numTriangles(numTriangles));

        while (numTriangles--) {

            MPointArray nonTweaked;
            MIntArray triangleVertices;
            MIntArray localIndex;
            status = itPolygon.getTriangle(numTriangles,
                                           nonTweaked,
                                           triangleVertices,
                                           MSpace::kObject );
            if (status != MS::kSuccess ) {
                CHECK_MSTATUS(status);
                continue;
            }

            if (triangleVertices.length() < 3) {
                MGlobal::displayWarning("Skipping degenerate polygon");
                continue;
            }

            localIndex = GetLocalIndex(polygonVertices, triangleVertices);

            int uvID[3];
            for ( int i = 0; i < 3; i++ ) {
                itPolygon.getUVIndex(localIndex[i],
                                     uvID[i],
                                     &UVSets[0] );

            }

            NormalRaster::Vertex polygon[3];

            for (int i = 0; i < 3; i++) {
                polygon[i].pos.x = u[uvID[i]] * ctx.width();
                polygon[i].pos.y = v[uvID[i]] * ctx.height();

                MVector normal = meshNormals[itPolygon.normalIndex(localIndex[i])];

                polygon[i].color.r = normal.x;
                polygon[i].color.g = normal.y;
                polygon[i].color.b = normal.z;
                polygon[i].color.a = 1.0;

            }

            ctx.draw_triangle(polygon[0], polygon[1], polygon[2]);

        }
    }
}

MStatus KSNormalLookup::compute(
const MPlug&      plug,
      MDataBlock& block ) 
{ 

    bool plugIsNormal = (plug == outNormalAttr) || (plug.parent() == outNormalAttr);
    bool plugIsFacingRatio = (plug == outFacingRatioAttr) || (plug.parent() == outFacingRatioAttr);
    if (!(plugIsNormal || plugIsFacingRatio)) {
		return MS::kUnknownParameter;
    }

    MStatus status = MS::kSuccess;

    // In the first version we used a kMesh attribute, which segfaulted inside
    // Shave when it was updating textures. We never figured out why. Instead,
    // we moved to a message attribute, and grab the shape ourselves.

    // Grab the shape from what is connected to the shapePlug.
    MObject shape;
    MPlug shapePlug(thisMObject(), shapeMessageAttr);
    if (!shapePlug.isConnected()) {
        // Reasonable failure case, so no API error message nessesary.
        return MS::kFailure;
    }
    MPlugArray shapeSourcePlugs;
    shapeSourcePlugs.clear();
    shapePlug.connectedTo(shapeSourcePlugs, true, false);
    if (!shapeSourcePlugs.length()) {
        CHECK_MSTATUS_AND_RETURN_IT(MS::kFailure);
    }
    shape = shapeSourcePlugs[0].node(); // There will only ever be one.

    // Grab the mesh from that shape.
    MFnMesh meshFn(shape, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);

    // Load the lookupPoint.
    MFloatVector& lookupPoint = block.inputValue(lookupPointAttr, &status).asFloatVector();
    if (status != MS::kSuccess) {
        // Reasonable failure case, so no API error message nessesary.
        return status;
    }

    float time = (float)block.inputValue(timeAttr, &status).asTime().as(MTime::kSeconds);

    MVector closestNormal;
    float2 & uv = block.inputValue( lookupUVAttr ).asFloat2();
    int cache_size = block.inputValue(cachSizeAttr).asInt();

    if (cache_size > 0) {

        if (cache_size != m_prev_cache_size || time != m_prev_time) {
            m_prev_cache_size = cache_size;
            m_prev_time = time;
            m_normal_raster.resize(cache_size, cache_size);
            get_normals(shape, m_normal_raster);

            for (int i = 0; i < 5; i++) {
                m_normal_raster.grow_edges();
            }

            #ifdef KSNORMAL_DEBUG
            std::ofstream ofile("ksnormal_data.rgba", std::ios::binary);
            ofile.write((char*) &m_normal_raster.data[0],
                          m_normal_raster.data.size() * sizeof(float));
            ofile.close();
            #endif
        }

        int x = uv[0] * m_normal_raster.width();
        int y = uv[1] * m_normal_raster.height();

        glm::vec4 color;
        m_normal_raster.read_pixel(x, y, color);
        closestNormal.x = color[0];
        closestNormal.y = color[1];
        closestNormal.z = color[2];

    } else {
        // Grab the closest normal to that point the slow way
        CHECK_MSTATUS_AND_RETURN_IT(meshFn.getClosestNormal(lookupPoint, closestNormal)); // <- ERROR IS HERE
        CHECK_MSTATUS_AND_RETURN_IT(closestNormal.normalize());
    }

    CHECK_MSTATUS_AND_RETURN_IT(closestNormal.normalize());

    // Calculate dot product between view vector and normal.
    MFloatVector& cameraLocation = block.inputValue(cameraLocationAttr, &status).asFloatVector();
    CHECK_MSTATUS_AND_RETURN_IT(status);
    MFloatVector lookupToCamera = cameraLocation - lookupPoint;
    CHECK_MSTATUS_AND_RETURN_IT(lookupToCamera.normalize());
    float dot = (lookupToCamera.x * closestNormal.x) + 
                (lookupToCamera.y * closestNormal.y) +
                (lookupToCamera.z * closestNormal.z);

    // Write normal.
    MDataHandle outNormalHandle = block.outputValue(outNormalAttr, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    MFloatVector& outNormal = outNormalHandle.asFloatVector();
    outNormal = closestNormal;
    outNormalHandle.setClean();

    // Write facing ratio.
    MDataHandle outFacingRatioHandle = block.outputValue(outFacingRatioAttr, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    float& outFacingRatio = outFacingRatioHandle.asFloat();
    outFacingRatio = dot;
    outFacingRatioHandle.setClean();

    return MS::kSuccess;

}


MStatus initializePlugin( MObject obj )
{
   const MString UserClassify( "utility/general" );

   MFnPlugin plugin( obj, PLUGIN_COMPANY, "4.5", "Any");
   CHECK_MSTATUS ( plugin.registerNode( "KSNormalLookup", KSNormalLookup::id, 
						KSNormalLookup::creator, KSNormalLookup::initialize,
						MPxNode::kDependNode, &UserClassify ) );

   return MS::kSuccess;
}


MStatus uninitializePlugin( MObject obj )
{
   MFnPlugin plugin( obj );
   CHECK_MSTATUS ( plugin.deregisterNode( KSNormalLookup::id ) );

   return MS::kSuccess;
}
