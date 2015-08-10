#ifndef GRADIENT_H
#define GRADIENT_H

#include "vertex.h"
#include <glm/glm.hpp>

namespace NormalRaster
{

class Gradient
{
public:
    Gradient(const Vertex &min_y,
             const Vertex &mid_y,
             const Vertex &max_y);
    glm::vec4 color(int index) const { return m_colors[index];}
    glm::vec4 colorstep_x() const { return m_colorstep_x; }
    glm::vec4 colorstep_y() const { return m_colorstep_y; }
private:
    glm::vec4 m_colorstep_x;
    glm::vec4 m_colorstep_y;
    glm::vec4 m_colors[3];

    float calc_xstep(const glm::vec3 &values,
                     const Vertex& min,
                     const Vertex& mid,
                     const Vertex& max,
                     float inv_dx);
    float calc_ystep(const glm::vec3 &values,
                     const Vertex& min,
                     const Vertex& mid,
                     const Vertex& max,
                     float inv_dy);
};

}

#endif // GRADIENT_H
