#include <math.h>

#include <maya/MDataBlock.h>
#include <maya/MDataHandle.h>
#include <maya/MFloatVector.h>
#include <maya/MFnMesh.h>
#include <maya/MFnMeshData.h>
#include <maya/MFnMessageAttribute.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnPlugin.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MIOStream.h>
#include <maya/MPlug.h>
#include <maya/MPlugArray.h>
#include <maya/MPxNode.h>
#include <maya/MString.h>
#include <maya/MTypeId.h>

#include "normal_raster/rendercontext.h"

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
    static MObject outNormalAttr;
    static MObject outFacingRatioAttr;
};

MTypeId KSNormalLookup::id('KSNL');


MObject KSNormalLookup::shapeMessageAttr;
MObject KSNormalLookup::cameraLocationAttr;
MObject KSNormalLookup::lookupPointAttr;
MObject KSNormalLookup::outNormalAttr;
MObject KSNormalLookup::outFacingRatioAttr;


void KSNormalLookup::postConstructor()
{
	setMPSafe(true);
}


KSNormalLookup::KSNormalLookup()
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

    // This one has a special name that is filled by the sampler.
    lookupPointAttr = nAttr.createPoint("pointWorld", "pw", &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(nAttr.setStorable(false));
    CHECK_MSTATUS(nAttr.setHidden(true));

    shapeMessageAttr = mAttr.create("shapeMessage", "rn", &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(mAttr.setStorable(false));

    cameraLocationAttr = nAttr.createPoint("cameraLocation", "cl", &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    CHECK_MSTATUS(nAttr.setStorable(false));

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
    CHECK_MSTATUS(addAttribute(lookupPointAttr));
    CHECK_MSTATUS(addAttribute(outNormalAttr));
    CHECK_MSTATUS(addAttribute(outFacingRatioAttr));

    CHECK_MSTATUS(attributeAffects(shapeMessageAttr, outNormalAttr));
    CHECK_MSTATUS(attributeAffects(lookupPointAttr, outNormalAttr));
    CHECK_MSTATUS(attributeAffects(shapeMessageAttr, outFacingRatioAttr));
    CHECK_MSTATUS(attributeAffects(cameraLocationAttr, outFacingRatioAttr));
    CHECK_MSTATUS(attributeAffects(lookupPointAttr, outFacingRatioAttr));

    return MS::kSuccess;
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

    // Grab the closest normal to that point.
    MVector closestNormal;
    CHECK_MSTATUS_AND_RETURN_IT(meshFn.getClosestNormal(lookupPoint, closestNormal)); // <- ERROR IS HERE
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
