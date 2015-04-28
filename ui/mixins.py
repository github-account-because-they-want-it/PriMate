__author__ = 'Mohammed Hamdy'

class CustomTouchMixin(object):

  def __init__(self, *args, **kwargs):
    super(CustomTouchMixin, self).__init__(*args, **kwargs)
    self.register_event_type("on_really_touch_down")

  def on_really_touch_down(self, touch):
    pass

class CustomTouchWidgetMixin(CustomTouchMixin):

  def on_touch_down(self, touch):
    if self.collide_point(*touch.pos) \
        and not self.disabled: # fix a bug in kivy that even a disabled widget still receives touches
      self.dispatch("on_really_touch_down", touch)
    return super(CustomTouchWidgetMixin, self).on_touch_down(touch)

class CustomTouchLayoutMixin(CustomTouchMixin):

  def on_touch_down(self, touch):
    for child in self.walk():
      if child is self: continue
      if child.collide_point(*touch.pos):
        # let the touch propagate to children
        return super(CustomTouchLayoutMixin, self).on_touch_down(touch)
    else:
      super(CustomTouchLayoutMixin, self).dispatch("on_really_touch_down", touch)
      return True
