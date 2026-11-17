#include "widgets.h"

#include "color.h"

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

namespace {

// Placeholder view: block background with the block name centred (replaced in a later task).
class BasicView : public BlockView {
 public:
  BasicView(lv_obj_t *parent, const Block &block, const Theme &theme) {
    this->id_ = block.id;
    this->root_ = lv_obj_create(parent);
    lv_obj_remove_style_all(this->root_);
    lv_obj_set_size(this->root_, theme.size, theme.size);
    lv_obj_set_pos(this->root_, 0, 0);
    lv_obj_remove_flag(this->root_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_bg_opa(this->root_, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(this->root_, lv_color_hex(block.bg), 0);

    lv_obj_t *label = lv_label_create(this->root_);
    lv_obj_set_width(label, theme.size * 7 / 10);
    lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_style_text_font(label, theme.text[static_cast<int>(block.font)], 0);
    lv_obj_set_style_text_color(label, lv_color_hex(text_color_for(block.bg)), 0);
    lv_label_set_text(label, block.name.c_str());
    lv_obj_center(label);
  }
};

}  // namespace

std::unique_ptr<BlockView> make_block_view(lv_obj_t *parent, const Block &block, const Theme &theme, ControlSink &,
                                           const LocalSources &) {
  return std::make_unique<BasicView>(parent, block, theme);
}

}  // namespace ha_controller
}  // namespace esphome
