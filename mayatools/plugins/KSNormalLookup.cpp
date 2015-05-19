#include <math.h>

#include <maya/MPxNode.h>
#include <maya/MIOStream.h>
#include <maya/MString.h>
#include <maya/MTypeId.h>
#include <maya/MPlug.h>
#include <maya/MDataBlock.h>
#include <maya/MDataHandle.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MFnMesh.h>
#include <maya/MFnMeshData.h>
#include <maya/MFloatVector.h>
#include <maya/MFnPlugin.h>


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
    static MObject referenceMeshAttr;
    static MObject cameraLocationAttr;
    static MObject lookupPointAttr;
    static MObject outNormalAttr;
    static MObject outFacingRatioAttr;
};

MTypeId KSNormalLookup::id( 0x8100e );


MObject KSNormalLookup::referenceMeshAttr;
MObject KSNormalLookup::cameraLocationAttr;
MObject KSNormalLookup::lookupPointAttr;
MObject KSNormalLookup::outNormalAttr;
MObject KSNormalLookup::outFacingRatioAttr;


void KSNormalLookup::postConstructor( )
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
    MStatus             stat;
    MFnNumericAttribute nAttr; 
    MFnTypedAttribute   typedAttr;

    // This one has a special name that is filled by the sampler.
    lookupPointAttr = nAttr.createPoint( "pointWorld", "pw");
    CHECK_MSTATUS ( nAttr.setStorable(false) );
    CHECK_MSTATUS ( nAttr.setHidden(true) );
    CHECK_MSTATUS ( nAttr.setReadable(true) );
    CHECK_MSTATUS ( nAttr.setWritable(true) );

    referenceMeshAttr = typedAttr.create( "referenceMesh", "rm", MFnMeshData::kMesh, &stat);
    CHECK_MSTATUS ( typedAttr.setStorable(false) );
    CHECK_MSTATUS ( typedAttr.setReadable(false) );
    CHECK_MSTATUS ( typedAttr.setWritable(true) );
    CHECK_MSTATUS ( typedAttr.setHidden(false) );

    cameraLocationAttr = nAttr.createPoint( "cameraLocation", "cl");
    CHECK_MSTATUS ( nAttr.setStorable(false) );
    CHECK_MSTATUS ( nAttr.setHidden(false) );
    CHECK_MSTATUS ( nAttr.setReadable(true) );
    CHECK_MSTATUS ( nAttr.setWritable(true) );

    outNormalAttr = nAttr.createColor( "outNormal", "on" );
    CHECK_MSTATUS ( nAttr.setStorable(false) );
    CHECK_MSTATUS ( nAttr.setHidden(false) );
    CHECK_MSTATUS ( nAttr.setReadable(true) );
    CHECK_MSTATUS ( nAttr.setWritable(false) );

    outFacingRatioAttr = nAttr.create( "outFacingRatio", "or", MFnNumericData::kFloat);
    CHECK_MSTATUS ( nAttr.setStorable(false) );
    CHECK_MSTATUS ( nAttr.setHidden(false) );
    CHECK_MSTATUS ( nAttr.setReadable(true) );
    CHECK_MSTATUS ( nAttr.setWritable(false) );

    CHECK_MSTATUS ( addAttribute(referenceMeshAttr) );
    CHECK_MSTATUS ( addAttribute(cameraLocationAttr) );
    CHECK_MSTATUS ( addAttribute(lookupPointAttr) );
    CHECK_MSTATUS ( addAttribute(outNormalAttr) );
    CHECK_MSTATUS ( addAttribute(outFacingRatioAttr) );

    CHECK_MSTATUS ( attributeAffects (referenceMeshAttr,  outNormalAttr) );
    CHECK_MSTATUS ( attributeAffects (lookupPointAttr,  outNormalAttr) );
    CHECK_MSTATUS ( attributeAffects (referenceMeshAttr,  outFacingRatioAttr) );
    CHECK_MSTATUS ( attributeAffects (cameraLocationAttr,  outFacingRatioAttr) );
    CHECK_MSTATUS ( attributeAffects (lookupPointAttr,  outFacingRatioAttr) );

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

    // Load the mesh.
    MDataHandle meshData = block.inputValue(referenceMeshAttr, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    MObject mesh = meshData.asMesh();
    MFnMesh meshFn(mesh);

    // Load the lookupPoint.
    MFloatVector& lookupPoint = block.inputValue(lookupPointAttr).asFloatVector();

    // Grab the closest normal to that point.
    MVector closestNormal;
    CHECK_MSTATUS_AND_RETURN_IT(meshFn.getClosestNormal(lookupPoint, closestNormal));
    CHECK_MSTATUS_AND_RETURN_IT(closestNormal.normalize());

    // Calculate dot product between view vector and normal.
    MFloatVector& cameraLocation = block.inputValue(cameraLocationAttr).asFloatVector();
    MFloatVector lookupToCamera = cameraLocation - lookupPoint;
    CHECK_MSTATUS_AND_RETURN_IT(lookupToCamera.normalize());
    float dot = (lookupToCamera.x * closestNormal.x) + 
                (lookupToCamera.y * closestNormal.y) +
                (lookupToCamera.z * closestNormal.z);

    // Write normal.
    MDataHandle outNormalHandle = block.outputValue(outNormalAttr);
    MFloatVector& outNormal = outNormalHandle.asFloatVector();
    outNormal = closestNormal;
    outNormalHandle.setClean();

    // Write facing ratio.
    MDataHandle outFacingRatioHandle = block.outputValue(outFacingRatioAttr);
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
