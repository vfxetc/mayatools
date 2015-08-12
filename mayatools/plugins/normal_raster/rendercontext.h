#ifndef RENDERCONTEXT_H
#define RENDERCONTEXT_H

#include "vertex.h"
#include "gradient.h"
#include "edge.h"

#include <vector>
#include <glm/glm.hpp>

namespace NormalRaster
{

class RenderContext
{
public:
    RenderContext() {}
    RenderContext(int width, int height);
    std::vector<float> data;
    void resize(int width, int height);
    void draw_pixel(int x, int y, const glm::vec4 &color);
    void read_pixel(int x, int y, glm::vec4 &color);
    void draw_triangle(const Vertex &v1, const Vertex &v2, const Vertex &v3);
    int width() const {return m_width;}
    int height() const {return m_height;}

private:
    void scan_triangle(const Vertex &min_y, const Vertex &mid_y, const Vertex &max_y, bool handedness);
    void scan_edge(const Gradient &grad, Edge &a, Edge &b, bool handedness);
    void draw_scanline(const Gradient &grad, const Edge &left, const Edge &right, int y);
    int m_width;
    int m_height;
};

}
#endif // RENDERCONTEXT_H
