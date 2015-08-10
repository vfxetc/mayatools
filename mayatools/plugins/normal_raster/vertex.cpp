#include "vertex.h"

using namespace NormalRaster;

float Vertex::area_x2(const Vertex &b, const Vertex &c) const
{

    float x1 = b.pos.x - pos.x;
    float y1 = b.pos.y - pos.y;

    float x2 = c.pos.x - pos.x;
    float y2 = c.pos.y - pos.y;

    return (x1 * y2 - x2 * y1);
}
