#include "pager.h"

// Needed for the lv_hit_test_info_t body (LV_EVENT_HIT_TEST); relies on the pinned LVGL 9.5 layout.
#include <src/core/lv_obj_event_private.h>

namespace esphome {
namespace ha_controller {

namespace {
struct HintSpec {
  int start;
  int end;
  Edge edge;
};
constexpr HintSpec HINTS[4] = {
    {350, 10, Edge::RIGHT},
    {80, 100, Edge::BOTTOM},
    {170, 190, Edge::LEFT},
    {260, 280, Edge::TOP},
};
constexpr int HINT_SIZE = 458;
}  // namespace

void Pager::attach(lv_obj_t *screen, int size, int edge_width) {
  this->size_ = size;
  this->edge_width_ = edge_width;
  SwipeConfig cfg;
  cfg.size = size;
  this->tracker_ = SwipeTracker(cfg);

  this->viewport_ = lv_obj_create(screen);
  lv_obj_remove_style_all(this->viewport_);
  lv_obj_set_size(this->viewport_, size, size);
  lv_obj_set_pos(this->viewport_, 0, 0);
  lv_obj_remove_flag(this->viewport_, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_remove_flag(this->viewport_, LV_OBJ_FLAG_CLICKABLE);

  for (int i = 0; i < 4; i++) {
    lv_obj_t *arc = lv_arc_create(lv_layer_top());
    lv_obj_remove_style_all(arc);
    lv_obj_set_size(arc, HINT_SIZE, HINT_SIZE);
    lv_obj_align(arc, LV_ALIGN_CENTER, 0, 0);
    lv_obj_remove_flag(arc, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_remove_flag(arc, LV_OBJ_FLAG_SCROLLABLE);
    lv_arc_set_rotation(arc, 0);
    lv_arc_set_bg_angles(arc, HINTS[i].start, HINTS[i].end);
    lv_obj_set_style_arc_width(arc, 6, LV_PART_MAIN);
    lv_obj_set_style_arc_color(arc, lv_color_white(), LV_PART_MAIN);
    lv_obj_set_style_arc_opa(arc, LV_OPA_60, LV_PART_MAIN);
    lv_obj_set_style_arc_opa(arc, LV_OPA_TRANSP, LV_PART_INDICATOR);
    lv_obj_set_style_bg_opa(arc, LV_OPA_TRANSP, LV_PART_KNOB);
    lv_obj_add_flag(arc, LV_OBJ_FLAG_HIDDEN);
    this->hints_[i] = arc;
  }

  this->edge_ = lv_obj_create(lv_layer_top());
  lv_obj_remove_style_all(this->edge_);
  lv_obj_set_size(this->edge_, size, size);
  lv_obj_set_pos(this->edge_, 0, 0);
  lv_obj_remove_flag(this->edge_, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag(this->edge_, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_flag(this->edge_, LV_OBJ_FLAG_ADV_HITTEST);
  lv_obj_add_event_cb(this->edge_, Pager::on_edge_event_, LV_EVENT_ALL, this);
}

void Pager::on_edge_event_(lv_event_t *e) {
  auto *self = static_cast<Pager *>(lv_event_get_user_data(e));
  if (lv_event_get_code(e) == LV_EVENT_DELETE)
    return;
  switch (lv_event_get_code(e)) {
    case LV_EVENT_HIT_TEST: {
      lv_hit_test_info_t *info = lv_event_get_hit_test_info(e);
      info->res = classify_edge(info->point->x, info->point->y, self->size_, self->edge_width_) != Edge::NONE;
      break;
    }
    case LV_EVENT_PRESSED:
      self->on_pressed_();
      break;
    case LV_EVENT_PRESSING:
      self->on_pressing_();
      break;
    case LV_EVENT_RELEASED:
    case LV_EVENT_PRESS_LOST:
      self->on_released_();
      break;
    default:
      break;
  }
}

const PageRef *Pager::page_at_(int x, int y) const {
  for (const auto &p : this->pages_) {
    if (p.x == x && p.y == y)
      return &p;
  }
  return nullptr;
}

const PageRef *Pager::current_page_() const {
  return this->current_idx_ >= 0 ? &this->pages_[this->current_idx_] : nullptr;
}

void Pager::on_pressed_() {
  if (!this->enabled_ || this->animating_)
    return;
  // A fresh press while a swipe is still tracked means the release was lost: drop the stale swipe.
  if (this->tracker_.active())
    this->abort_swipe_();
  const PageRef *cur = this->current_page_();
  lv_indev_t *indev = lv_indev_active();
  if (cur == nullptr || indev == nullptr)
    return;
  lv_point_t p;
  lv_indev_get_point(indev, &p);
  Edge edge = classify_edge(p.x, p.y, this->size_, this->edge_width_);
  if (edge == Edge::NONE)
    return;
  GridStep step = step_for(edge);
  const PageRef *target = this->page_at_(cur->x + step.dx, cur->y + step.dy);
  this->dx_ = step.dx;
  this->dy_ = step.dy;
  this->target_idx_ = target != nullptr ? static_cast<int>(target - this->pages_.data()) : -1;
  this->tracker_.begin(edge, target != nullptr, p.x, p.y, lv_tick_get());
  if (target != nullptr)
    lv_obj_remove_flag(target->obj, LV_OBJ_FLAG_HIDDEN);
  this->place_(0);
}

void Pager::on_pressing_() {
  if (!this->tracker_.active())
    return;
  lv_indev_t *indev = lv_indev_active();
  if (indev == nullptr)
    return;
  lv_point_t p;
  lv_indev_get_point(indev, &p);
  this->place_(this->tracker_.update(p.x, p.y, lv_tick_get()));
}

void Pager::on_released_() {
  if (!this->tracker_.active())
    return;
  int offset = this->tracker_.progress();
  bool commit = this->tracker_.release(lv_tick_get()) && this->target_idx_ >= 0;
  this->place_(offset);
  int remaining = commit ? this->size_ - offset : offset;
  if (remaining <= 0) {
    this->finish_(commit);
    return;
  }
  this->animating_ = true;
  this->anim_commit_ = commit;
  lv_anim_t a;
  lv_anim_init(&a);
  lv_anim_set_var(&a, this);
  lv_anim_set_exec_cb(&a, Pager::anim_exec_);
  lv_anim_set_values(&a, offset, commit ? this->size_ : 0);
  lv_anim_set_duration(&a, settle_duration_ms(remaining, this->size_));
  lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
  lv_anim_set_completed_cb(&a, Pager::anim_done_);
  lv_anim_start(&a);
}

void Pager::anim_exec_(void *var, int32_t value) { static_cast<Pager *>(var)->place_(value); }

void Pager::anim_done_(lv_anim_t *a) {
  auto *self = static_cast<Pager *>(a->var);
  self->finish_(self->anim_commit_);
}

void Pager::place_(int offset) {
  const PageRef *cur = this->current_page_();
  if (cur != nullptr)
    lv_obj_set_pos(cur->obj, -this->dx_ * offset, -this->dy_ * offset);
  if (this->target_idx_ >= 0) {
    const PageRef &t = this->pages_[this->target_idx_];
    lv_obj_set_pos(t.obj, this->dx_ * (this->size_ - offset), this->dy_ * (this->size_ - offset));
  }
}

void Pager::finish_(bool commit) {
  this->animating_ = false;
  const PageRef *cur = this->current_page_();
  if (commit && this->target_idx_ >= 0) {
    if (cur != nullptr)
      lv_obj_add_flag(cur->obj, LV_OBJ_FLAG_HIDDEN);
    this->current_idx_ = this->target_idx_;
    this->current_id_ = this->pages_[this->current_idx_].id;
  } else if (this->target_idx_ >= 0) {
    lv_obj_add_flag(this->pages_[this->target_idx_].obj, LV_OBJ_FLAG_HIDDEN);
  }
  this->target_idx_ = -1;
  this->dx_ = 0;
  this->dy_ = 0;
  cur = this->current_page_();
  if (cur != nullptr)
    lv_obj_set_pos(cur->obj, 0, 0);
  this->refresh_hints_();
}

// Stops any swipe or animation and puts the current page back in place.
void Pager::abort_swipe_() {
  lv_anim_delete(this, Pager::anim_exec_);
  this->tracker_.reset();
  if (this->target_idx_ >= 0 && this->target_idx_ < static_cast<int>(this->pages_.size()))
    lv_obj_add_flag(this->pages_[this->target_idx_].obj, LV_OBJ_FLAG_HIDDEN);
  this->finish_(false);
}

void Pager::set_pages(std::vector<PageRef> pages, const std::string &show_id) {
  // Cancel first: the old page objects may already be gone and are never touched again.
  lv_anim_delete(this, Pager::anim_exec_);
  this->tracker_.reset();
  this->animating_ = false;
  this->target_idx_ = -1;
  this->dx_ = 0;
  this->dy_ = 0;
  this->current_idx_ = -1;
  this->pages_ = std::move(pages);
  this->current_id_.clear();
  for (size_t i = 0; i < this->pages_.size(); i++) {
    lv_obj_add_flag(this->pages_[i].obj, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_pos(this->pages_[i].obj, 0, 0);
    if (this->pages_[i].id == show_id)
      this->current_idx_ = static_cast<int>(i);
  }
  if (this->current_idx_ < 0 && !this->pages_.empty())
    this->current_idx_ = 0;
  if (this->current_idx_ >= 0) {
    lv_obj_remove_flag(this->pages_[this->current_idx_].obj, LV_OBJ_FLAG_HIDDEN);
    this->current_id_ = this->pages_[this->current_idx_].id;
  }
  this->refresh_hints_();
}

void Pager::set_enabled(bool enabled) {
  if (this->enabled_ == enabled)
    return;
  this->enabled_ = enabled;
  if (!enabled)
    this->abort_swipe_();
  if (this->edge_ != nullptr) {
    if (enabled)
      lv_obj_remove_flag(this->edge_, LV_OBJ_FLAG_HIDDEN);
    else
      lv_obj_add_flag(this->edge_, LV_OBJ_FLAG_HIDDEN);
  }
  this->refresh_hints_();
}

void Pager::refresh_hints_() {
  const PageRef *cur = this->current_page_();
  for (int i = 0; i < 4; i++) {
    if (this->hints_[i] == nullptr)
      continue;
    bool show = false;
    if (this->enabled_ && cur != nullptr) {
      GridStep s = step_for(HINTS[i].edge);
      show = this->page_at_(cur->x + s.dx, cur->y + s.dy) != nullptr;
    }
    if (show)
      lv_obj_remove_flag(this->hints_[i], LV_OBJ_FLAG_HIDDEN);
    else
      lv_obj_add_flag(this->hints_[i], LV_OBJ_FLAG_HIDDEN);
  }
}

}  // namespace ha_controller
}  // namespace esphome
