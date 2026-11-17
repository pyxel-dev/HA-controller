#include "widgets.h"

#include "views.h"

namespace esphome {
namespace ha_controller {

BlockView::~BlockView() {
  if (this->root_ != nullptr)
    lv_obj_delete(this->root_);
}

bool BlockView::owns(const std::string &id) const { return id == this->id_; }
void BlockView::apply(const StateUpdate &, uint32_t) {}
void BlockView::on_local_update() {}
void BlockView::loop(uint32_t) {}

std::unique_ptr<BlockView> make_block_view(lv_obj_t *parent, const Block &block, const Theme &theme, ControlSink &sink,
                                           const LocalSources &local) {
  switch (block.widget) {
    case Widget::LIGHT:
      return make_light_view(parent, block, theme, sink);
    case Widget::CLIMATE:
      return make_climate_view(parent, block, theme, sink);
    case Widget::CUSTOM:
      break;
  }
  return make_custom_view(parent, block, theme, local);
}

}  // namespace ha_controller
}  // namespace esphome
