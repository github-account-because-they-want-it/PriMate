__author__ = 'Mohammed Hamdy'

from os.path import dirname, join
import csv, random
from functools import partial
from datetime import datetime
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.button import Button
from kivy.uix.video import Video
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.core.window import Window
from lib.util import dispense_pellet, SubjectManager, TrialData, variablize_string, get_background_placeholder
from ui.mixins import CustomTouchWidgetMixin

class SubjectButton(Button):
  pass

class SubjectScreen(Screen):

  def __init__(self, subject_reader, *args, **kwargs):
    super(SubjectScreen, self).__init__(*args, **kwargs)
    # emit an event when a subject button is pressed
    self.register_event_type("on_subject_selected")
    # fill out the subjects screen from subjects.json
    subject_container = self.ids.subject_container
    name_config_file = join(dirname(__file__), "config", "subjects.json")
    for subject in subject_reader.get_subjects():
      button_subject = SubjectButton(text=subject)
      if subject_reader.is_subject_done(subject):
        button_subject.disabled = True
      else:
        button_subject.bind(on_press=self.handle_subject_selected)
      subject_container.add_widget(button_subject)

  def handle_subject_selected(self, button):
    self.dispatch("on_subject_selected", button)

  def on_subject_selected(self, button):
    pass

class StartTrialScreen(Screen):
  pass

class TouchAwareVideo(CustomTouchWidgetMixin, Video):

  def on_state(self, instance, state):
    super(TouchAwareVideo, self).on_state(instance, state)
    # keep the video running continuously
    if state == "stop":
      self.state = "play"

class TouchAwareWidget(CustomTouchWidgetMixin, Widget):
  pass

class TouchAwareImage(CustomTouchWidgetMixin, Image):
  pass

class TrialScreen(Screen):

  def __init__(self, *args, **kwargs):
    super(TrialScreen, self).__init__(*args, **kwargs)
    self.register_event_type("on_left_card_chosen")
    self.register_event_type("on_right_card_chosen")
    # bind all image places. 2 to left and right and the rest is background touches
    self._video_touches = 0
    self._background_touches = 0
    self._trial_start_time = None
    self._condition = None
    self._image_left_card = None
    self._image_right_card = None

  def left_card_selected(self, image, touch):
    self._enable_cards(False)
    self._image_right_card.opacity = 0
    self.dispatch("on_left_card_chosen", self._calculate_time_till_choice())

  def right_card_selected(self, image, touch):
    self._enable_cards(False)
    self._image_left_card.opacity = 0
    self.dispatch("on_right_card_chosen", self._calculate_time_till_choice())

  def on_left_card_chosen(self, time_taken):
    pass

  def on_right_card_chosen(self, time_taken):
    pass

  def _calculate_time_till_choice(self):
    return (datetime.now() - self._trial_start_time).total_seconds()

  def set_condition(self, condition):
    # condition: util.Condition()
    self.ids.video_condition.source = condition.video
    self._condition = condition

  def on_pre_enter(self):
    if self._image_left_card is not None: # at first time the trial screen is shown
      self._enable_cards(True)
      self._show_cards(True)
    # randomize the placement of cards and bind images without content as background touches
    image_places = self._get_image_places()
    image_index_left, image_index_right = 0, 0
    # ensure chosen placements are not the same
    while image_index_left == image_index_right:
      image_index_left = random.randrange(0, len(image_places))
      image_index_right = random.randrange(0, len(image_places))
    image_place_left = image_places[image_index_left]
    image_place_right = image_places[image_index_right]
    image_places.remove(image_place_left)
    image_places.remove(image_place_right)
    # now what's left in image_places is background touch detectors
    condition_images = self._condition.get_associated_images()
    image_place_left.bind(on_really_touch_down=self.left_card_selected)
    image_place_left.source = condition_images["left_image"]
    image_place_right.bind(on_really_touch_down=self.right_card_selected)
    image_place_right.source = condition_images["right_image"]
    for image_place in image_places:
      image_place.bind(on_really_touch_down=self.on_background_touched)
      image_place.source = get_background_placeholder()
    self._image_left_card = image_place_left
    self._image_right_card = image_place_right

  def on_enter(self):
    self.ids.video_condition.state = "play"
    self._trial_start_time = datetime.now()

  def on_video_touched(self, *args):
    self._video_touches += 1

  def on_background_touched(self, *args):
    self._background_touches += 1

  def get_touches(self):
    return self._background_touches, self._video_touches

  def _get_image_places(self):
    return [self.ids.image_place_1, self.ids.image_place_2, self.ids.image_place_3, self.ids.image_place_4,
            self.ids.image_place_5, self.ids.image_place_6, self.ids.image_place_7]

  def _enable_cards(self, status):
    self._image_left_card.disabled = not status
    self._image_right_card.disabled = not status

  def _show_cards(self, status):
    if status is True:
      opacity = 1.0
    else:
      opacity = 0
    self._image_left_card.opacity = opacity
    self._image_right_card.opacity = opacity

class BlankScreen(Screen):
  pass

class ConditionCompleteScreen(Screen):

  def __init__(self, *args, **kwargs):
    super(ConditionCompleteScreen, self).__init__(*args, **kwargs)
    self.register_event_type("on_key_pressed")
    keyboard = Window.request_keyboard(self._keyboard_closed, self, "text")
    keyboard.bind(on_key_down=self._key_pressed)

  def set_subject_and_condition(self, subject, condition):
    self.ids.label_condition.text = "'{}' completed condition '{}'\nPress any key to exit".format(subject, condition)

  def _keyboard_closed(self):
    pass

  def _key_pressed(self, keyboard, keycode, text, modifiers):
    self.dispatch("on_key_pressed")

  def on_key_pressed(self):
    pass

class PriMateApp(App):

  _total_trial_count = 2
  _inter_pellet_wait_seconds = 0.5

  def __init__(self, *args, **kwargs):
    super(PriMateApp, self).__init__(*args, **kwargs)
    self._count_left_card_chosen = 0
    self._count_right_card_chosen = 0
    self._index_current_trial = None
    self._csv_reader_non_risky = csv.reader(open(join(dirname(__file__), "config", "EPGT_Payoff.csv"), 'r'))
    self._csv_reader_risky = csv.reader(open(join(dirname(__file__), "config", "EPGT_Payoff_Risky.csv"), 'r'))
    self._subject_manager = SubjectManager(self._total_trial_count)
    self._current_subject = None
    self._current_condition = None
    self._current_trial_data = None

  def build(self):
    Builder.load_file("ui/screens.kv")
    manager_screen = ScreenManager(transition=NoTransition())
    screen_subject = SubjectScreen(self._subject_manager, name="subject")
    screen_subject.bind(on_subject_selected=self.start_trial_screen)
    manager_screen.add_widget(screen_subject)
    manager_screen.add_widget(StartTrialScreen(name="start_trial"))
    screen_trial = TrialScreen(name="trial")
    screen_trial.bind(on_left_card_chosen=self.on_left_card_chosen)
    screen_trial.bind(on_right_card_chosen=self.on_right_card_chosen)
    manager_screen.add_widget(screen_trial)
    manager_screen.add_widget(BlankScreen(name="blank_screen"))
    screen_condition_complete = ConditionCompleteScreen(name="condition_complete")
    screen_condition_complete.bind(on_key_pressed=self.stop)
    manager_screen.add_widget(screen_condition_complete)
    return manager_screen

  def start_trial_screen(self, screen_subject, button_subject):
    # now we have a subject selected, we can get it's next condition and inform other screens
    self._current_subject = button_subject.text
    # write a csv with header for the new subject. only created if the subject ran no trials before
    if len(self._subject_manager.get_conditions(self._current_subject)) == 0:
      with open(self._get_stats_file_name(), 'w') as stats_file:
        csv_writer = csv.writer(stats_file)
        csv_writer.writerow(["Trial Index", "Date", "Time", "Subject", "Condition", "Card Selected", "Background Touches",
                              "Video Touches", "Time till Choice (sec)"])
    condition_subject = self._subject_manager.get_unfinished_condition(self._current_subject)
    self._index_current_trial = condition_subject.next_trial_index
    self._skip_payoff_lines()
    self._current_condition = condition_subject
    self.root.get_screen("trial").set_condition(condition_subject)
    self.root.get_screen("condition_complete").set_subject_and_condition(self._current_subject, condition_subject.name)
    self._restart_trial(0)

  def on_left_card_chosen(self, screen, time_till_choice):
    # called from kv when left card chosen
    self._update_trial_data(time_till_choice, "Green Card")
    count_pellets = int(next(self._csv_reader_non_risky)[0])
    self._dispense_pellets(count_pellets)
    self._count_left_card_chosen += 1
    self._wait_till_five_seconds(count_pellets)

  def on_right_card_chosen(self, screen, time_till_choice):
    # also called from kv. this is the risky card
    self._update_trial_data(time_till_choice, "Red Card")
    count_pellets = int(next(self._csv_reader_risky)[0])
    self._dispense_pellets(count_pellets)
    self._count_right_card_chosen += 1
    self._wait_till_five_seconds(count_pellets)

  def _wait_till_five_seconds(self, count_pellets):
    # complete the time taken to dispense pellets up for 5 seconds
    Clock.schedule_once(self._go_to_blank, 5 - self._inter_pellet_wait_seconds * count_pellets)

  def _go_to_blank(self, elapsed):
    self.root.current = "blank_screen"
    # keep the blank for 10 seconds
    Clock.schedule_once(self._restart_trial, 10)

  def _dispense_pellets(self, count, tick_time=0):
    if count == 0: return
    dispense_pellet()
    Clock.schedule_once(partial(self._dispense_pellets, count - 1), self._inter_pellet_wait_seconds)

  def _restart_trial(self, elapsed):
    if self._index_current_trial == self._total_trial_count:
      self._index_current_trial = 0
      self._subject_manager.save()
      self.root.current = "condition_complete"
    else:
      self._current_trial_data = TrialData(self._current_subject, self._index_current_trial, self._current_condition.name)
      self.root.current = "start_trial"
      self._subject_manager.passed_trial(self._current_subject, self._current_condition)
    self._index_current_trial += 1

  def _update_trial_data(self, time_till_choice, card_name):
    self._current_trial_data.time_till_selection = time_till_choice
    self._current_trial_data.card_selected = card_name
    screen_trial = self.root.get_screen("trial")
    background_touches, video_touches = screen_trial.get_touches()
    self._current_trial_data.background_touches = background_touches
    self._current_trial_data.video_touches = video_touches
    self._write_trial_data()

  def _write_trial_data(self):
    with open(self._get_stats_file_name(), 'a') as stats_file:
      csv_writer = csv.writer(stats_file)
      trial = self._current_trial_data
      csv_writer.writerow([trial.trial_index + 1, trial.date, trial.time, trial.subject, trial.condition, trial.card_selected,
                              trial.background_touches, trial.video_touches, trial.time_till_selection])

  def _get_stats_file_name(self):
    # stats file name should include the name of the current subject
    return join(dirname(__file__), "config", "stats_{}.csv"
        .format(variablize_string(self._current_subject)))

  def _skip_payoff_lines(self):
    # match the current payoff with the current index
    for _ in range(self._index_current_trial):
      next(self._csv_reader_risky)
      next(self._csv_reader_non_risky)

  def on_stop(self):
    self._subject_manager.save()


if __name__ == "__main__":
  from kivy.core.window import Window
  import tkinter
  root = tkinter.Tk()
  Window.fullscreen = True
  Window.size = (root.winfo_screenwidth(), root.winfo_screenheight())
  PriMateApp().run()