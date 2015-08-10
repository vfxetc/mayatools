#include "gradient.h"

using namespace NormalRaster;

Gradient::Gradient(const Vertex &min_y,
                   const Vertex &mid_y,
                   const Vertex &max_y)
{

    float inv_dx = 1.0f / (
              ((mid_y.pos.x - max_y.pos.x) *
               (min_y.pos.y - max_y.pos.y)) -
              ((min_y.pos.x - max_y.pos.x) *
               (mid_y.pos.y - max_y.pos.y))
              );

    float inv_dy = -inv_dx;

    m_colors[0] = min_y.color;
    m_colors[1] = mid_y.color;
    m_colors[2] = max_y.color;

    for (int i =0; i < 4; i++) {
        glm::vec3 values(m_colors[0][i],
                         m_colors[1][i],
                         m_colors[2][i]);

        m_colorstep_x[i] = calc_xstep(values, min_y, mid_y, max_y, inv_dx);
        m_colorstep_y[i] = calc_ystep(values, min_y, mid_y, max_y, inv_dy);
    }

}

float Gradient::calc_xstep(const glm::vec3 &values,
                           const Vertex& min,
                           const Vertex& mid,
                           const Vertex& max,
                           float inv_dx)
{
    return (((values[1] - values[2]) *
            (min.pos.y - max.pos.y)) -
            ((values[0] - values[2]) *
            (mid.pos.y - max.pos.y))) * inv_dx;
}

float Gradient::calc_ystep(const glm::vec3 &values,
                           const Vertex& min,
                           const Vertex& mid,
                           const Vertex& max,
                           float inv_dy)
{
    return (((values[1] - values[2]) *
            (min.pos.x - max.pos.x)) -
            ((values[0] - values[2]) *
            (mid.pos.x - max.pos.x))) * inv_dy;
}
