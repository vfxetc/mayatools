#include "rendercontext.h"
#include <iostream>
#include <glm/gtx/string_cast.hpp>

using namespace NormalRaster;

RenderContext::RenderContext(int width, int height) :
    m_width(width),
    m_height(height)
{
    data.resize(width * height *4);
}

void RenderContext::resize(int width, int height)
{
    data.resize(width * height *4);
    m_width = width;
    m_height = height;
}

void RenderContext::draw_pixel(int x, int y, const glm::vec4 &color)
{
    if (y < 0 || y >= m_height)
        return;

    if (x < 0 || x >= m_width)
        return;

    int index = (x + (y * m_width)) * 4;

    //if (data[index + 3] != 0) {
    //    std::cerr << x << " " << y <<" overdraw\n" ;
    //}

    data[index    ] = color.r;
    data[index + 1] = color.g;
    data[index + 2] = color.b;
    data[index + 3] = color.a;


}

void RenderContext::draw_triangle(const Vertex &v1, const Vertex &v2, const Vertex &v3)
{
    const Vertex *min = &v1;
    const Vertex *mid = &v2;
    const Vertex *max = &v3;

    // Sort triangles in y
    if(max->pos.y < mid->pos.y) {
        const Vertex *temp = max;
        max = mid;
        mid = temp;
    }

    if(mid->pos.y < min->pos.y) {
        const Vertex *temp = mid;
        mid = min;
        min = temp;
    }

    if(max->pos.y < mid->pos.y) {
        const Vertex *temp = max;
        max = mid;
        mid = temp;
    }

    //std::cerr << "min " << glm::to_string(min.pos) << "\n";
    //std::cerr << "mid " << glm::to_string(mid.pos) << "\n";
    //std::cerr << "max " << glm::to_string(max.pos) << "\n";

    scan_triangle(*min, *mid, *max,
                  min->area_x2(*max, *mid) >= 0);
}

void RenderContext::scan_triangle(const Vertex &min_y,
                                  const Vertex &mid_y,
                                  const Vertex &max_y,
                                  bool handedness)
{
    Gradient grad(min_y, mid_y, max_y);
    Edge top_bottom(grad, min_y, max_y, 0);
    Edge top_middle(grad, min_y, mid_y, 0);
    Edge middle_bottom(grad, mid_y, max_y, 1);

    scan_edge(grad, top_bottom, top_middle, handedness);
    scan_edge(grad, top_bottom, middle_bottom, handedness);

}

void RenderContext::scan_edge(const Gradient &grad,
                              Edge &a,
                              Edge &b,
                              bool handedness)
{

    Edge *left = &a;
    Edge *right = &b;

    if (handedness) {
        Edge *temp = left;
        left = right;
        right = temp;
    }

    int ystart = b.ystart();
    int yend = b.yend();

    for (int y = ystart; y < yend; y++) {
        draw_scanline(grad, *left, *right, y);
        left->step();
        right->step();
    }
}

void RenderContext::draw_scanline(const Gradient &grad,
                                  const Edge &left,
                                  const Edge &right,
                                  int y)
{
    int xmin = (int)ceil(left.x());
    int xmax = (int)ceil(right.x());

    float xprestep = xmin - left.x();

    glm::vec4 mincolor = left.color() + (grad.colorstep_x() * xprestep);
    glm::vec4 maxcolor = right.color() + (grad.colorstep_x() * xprestep);

    float lerp = 0.0;
    float lerp_step = 1.0/(float)(xmax - xmin);

    //std::cerr << xmin << "-" << xmax << "\n";

    //xmin = std::max(0, xmin);
    //xmax = std::min(m_width, xmax);

    for(int x = xmin; x < xmax; x++) {
        glm::vec4 c = (maxcolor * lerp) + (mincolor * (1- lerp));
        draw_pixel(x,y, c);
        lerp += lerp_step;
    }
}
