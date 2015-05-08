__author__ = 'Mohammed Hamdy'

from os.path import dirname, join, splitext, basename
from os import listdir
from datetime import datetime
import json, subprocess

_config_dir = join(dirname(dirname(__file__)), "config")

def dispense_pellet():
  batch_despenser = join(_config_dir, "dispenser.bat")
  subprocess.Popen(batch_despenser)

def get_video_dir():
  return join(dirname(dirname(__file__)), "res", "videos")

def get_images_dir():
  return join(dirname(dirname(__file__)), "res", "images")

def get_background_placeholder():
  return join(get_images_dir(), "placeholder.png")

class SubjectManager(object):
  """
  Keeps track of subjects and conditions in `subjects.json'.
    Like which conditions has been run for each subject.
  """

  _default_conditions = [{"name":"high_ranking"}, {"name":"low_ranking"}, {"name":"nonsocial"}, {"name":"stranger"}]

  def __init__(self, total_trial_count):
    self._total_trial_count = total_trial_count
    self._subjects_file_path = join(dirname(dirname(__file__)), "config", "subjects.json")
    dir_conditions = get_video_dir()
    self._full_path_videos = [join(dir_conditions, video_name) for video_name in listdir(dir_conditions)]
    self._subject_infos = json.load(open(self._subjects_file_path, 'r', newline=''))

  def get_subjects(self):
    return [subject["name"] for subject in self._subject_infos]

  def get_conditions(self, subject):
    subject_info = self._get_subject_info(subject)
    video_paths = []
    conditions = subject_info.get("conditions", []) # user might add new subjects with only a name to subjects.json
    condition_names = [condition["name"] for condition in conditions]
    for condition_name in condition_names:
      for condition_video in self._full_path_videos:
        if condition_name in condition_video:
          video_paths.append(condition_video)
    return [Condition(video_path) for video_path in video_paths]

  def is_subject_done(self, subject):
    subject_info  = self._get_subject_info(subject)
    return len(self._get_playable_conditions(subject_info)) == 0

  def _get_played_conditions(self, subject_info):
    return list(filter(lambda condition: condition.get("played", False), subject_info.get("conditions", [])))

  def get_unfinished_condition(self, subject):
    # assign a condition to the subject in the order specified in subjects.json
    # this assumes that the caller knows what it's doing. it won't check if there's no conditions left
    subject_info = self._get_subject_info(subject)
    playable_conditions = self._get_playable_conditions(subject_info)
    played_conditions = self._get_played_conditions(subject_info)
    target_condition = playable_conditions[0]  # choose highest priority (last_played) or just first
    condition_video_path = target_condition.video
    # read the existing trial index or zero out
    target_condition_name = target_condition.condition_name
    for condition in played_conditions:
      if condition["name"] == target_condition_name:
        next_trial_index = condition["next_trial_index"]
        break
    else:
      next_trial_index = 0
    # the last_played property should only exist for a single condition
    # update the played condition
    self._update_condition_dict(subject_info, target_condition.condition_name,
                                {"next_trial_index": next_trial_index, "last_played": True, "played":True})
    return Condition(condition_video_path, next_trial_index)

  def passed_trial(self, subject, condition):
    # should be called whenever a subject passes a trial
    subject_info = self._get_subject_info(subject)
    condition_info = self._get_condition_info(subject_info, condition.condition_name)
    condition_info["next_trial_index"] += 1
    # remove resumption possibility from condition when it's finished
    if condition_info["next_trial_index"] == self._total_trial_count:
      condition_info.pop("last_played", None)

  def save(self):
    # this should be called at the end of each condition (200 trials)
    with open(self._subjects_file_path, 'w', newline='') as subjects_writer:
      json.dump(self._subject_infos, subjects_writer, indent=2)

  def _get_subject_info(self, subject):
    for subject_info in self._subject_infos:
      if subject_info["name"] == subject:
        return subject_info

  def _get_playable_conditions(self, subject_info):
    # playable conditions are conditions never before played or has a trial index less than total trial count
    # this returns the list of video names that can be played
    playable_conditions = []
    # first add never before played conditions
    subject_played_condition_names = [condition["name"] for condition in self._get_played_conditions(subject_info)]
    for condition in subject_info.get("conditions"):
      condition_name = condition["name"]
      full_path_video = self._video_from_condition_name(condition_name)
      if condition_name in subject_played_condition_names:
        next_trial_index = condition.get("next_trial_index", 0)
        last_played = condition.get("last_played", False)
        if next_trial_index < self._total_trial_count:
          playable_conditions.append(full_path_video)
        elif last_played:
          # give last played condition a priority by inserting it first into playable conditions
          playable_conditions.insert(0, full_path_video)
      else:
        # never before played condition
        playable_conditions.append(full_path_video)
    return [Condition(video_path) for video_path in playable_conditions]

  def _update_condition_dict(self, subject_info, condition_name, props):
    target_dict = self._get_condition_info(subject_info, condition_name)
    target_dict.update(props)

  def _get_condition_info(self, subject_info, condition_name):
    subject_info.setdefault("conditions", self._default_conditions)
    return [condition_dict for condition_dict in subject_info.get("conditions") if
            condition_dict["name"] == condition_name][0]

  def _video_from_condition_name(self, condition_name):
    return [video_path for video_path in self._full_path_videos if condition_name in video_path][0]


def variablize_string(s):
  # convert "Hello World" to "hello_world"
  return s.lower().replace(' ', '_')

class Condition(object):

  def __init__(self, video, next_trial_index=0):
    video_name = splitext(basename(video))[0]
    self.name = ' '.join([word.capitalize() for word in video_name.split('_')])
    self.condition_name = video_name  # this should be used to name the condition in subjects.json
    self.video = video
    self.next_trial_index = next_trial_index

  def get_associated_images(self):
    # each condition has 2 associated images.
    image_dir = get_images_dir()
    if "high_ranking" in self.video:
      return {"left_image":join(image_dir, "bluecogs.png"), "right_image":join(image_dir, "purpleleaf.png")}
    elif "low_ranking" in self.video:
      return {"left_image":join(image_dir, "redwhitesquares.png"), "right_image":join(image_dir, "irishgreen.png")}
    elif "stranger" in self.video:
      return {"left_image":join(image_dir, "greenbrownleaves.png"), "right_image":join(image_dir, "moon.png")}
    elif "nonsocial" in self.video:
      return {"left_image":join(image_dir, "purplediamond.png"), "right_image":join(image_dir, "snowflake.png")}

class TrialData(object):

  def __init__(self, subject, trial_index, condition):
    trial_datetime = datetime.now()
    self.date = trial_datetime.strftime("%m-%d-%y")
    self.time = trial_datetime.strftime("%H:%M:%S %p")
    self.subject = subject
    self.condition = condition
    self.trial_index = trial_index
    self.background_touches = 0
    self.video_touches = 0
    self.time_till_selection = None
    self.card_selected = None
    self.pellets_dispensed = 0