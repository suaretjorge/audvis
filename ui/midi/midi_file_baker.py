import os
import random
import re


def _testing_mergetracks(mid):
    import mido
    result = []
    if mid.type == 0:  # single track midi file type
        msgs = _testing_single_track(mid, mid.tracks[0])
        result.append({'name': mid.tracks[0].name, 'msgs': msgs})
    elif mid.type == 1:  # multi track midi file type
        for track in mid.tracks[1:]:
            # print('TRCK', track)
            msgs = _testing_single_track(mid, mido.midifiles.tracks.merge_tracks([mid.tracks[0], track]))
            result.append({'name': track.name, 'msgs': msgs})
    else:
        raise Exception('MIDI type 2 (asynchronous) not supported')

    return result


def _testing_single_track(mid, track):
    import mido
    timer = 0
    tempo = 500_000  # default 120 BPM
    result = []
    for msg in track:
        if msg.time > 0:
            timer += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
        if msg.type == 'set_tempo':
            tempo = msg.tempo
        if msg.type in ('note_on', 'note_off'):
            result.append(msg.copy(time=timer))
    return result


def _generate_track_name(orig_track_name, track_index, midifile):
    if type(orig_track_name) == str:
        orig_track_name = re.sub("[^a-zA-Z -_]+", "", orig_track_name)  # remove special characters
    if not orig_track_name:
        orig_track_name = "Track {}".format(track_index + 1)
    iii = 1
    name = orig_track_name
    while iii < 1000 and (name in midifile.tracks):
        name = "{}.{:03d}".format(orig_track_name, iii)
        iii += 1
    return name


def bake(scene, filepath: str, strip_silent_start: bool):
    import mido

    mid = mido.midifiles.MidiFile(filename=filepath, ticks_per_beat=480, charset='latin1')

    fps = scene.render.fps / scene.render.fps_base

    midifile = scene.audvis.midi_file.midi_files.add()
    scene.audvis.midi_file.list_index = len(scene.audvis.midi_file.midi_files) - 1
    for i in range(1000):
        name = os.path.basename(filepath)
        if i > 0:
            name += ".{0:03d}".format(i)
        if name not in scene.audvis.midi_file.midi_files:
            midifile.name = name
            break
        if i == 999:
            midifile.name = name + str(random.randint())
    midifile.time_length = mid.length
    midifile.fps_when_loaded = fps
    overall_offset_time = 0.0
    if strip_silent_start:
        timer = 0.0
        for msg in mid:
            timer += msg.time
            if msg.type == 'note_on':
                overall_offset_time = -timer
                break
    for track_index, track in enumerate(_testing_mergetracks(mid)):
        track_item = midifile.tracks.add()
        name = _generate_track_name(track['name'], track_index, midifile)
        track_item.name = name
        counter = 0
        for msg in track['msgs']:
            if msg.type in ('note_on', 'note_off'):
                counter += 1
                key = "ch{}_n{}".format(msg.channel + 1, msg.note)
                keyframe_key = '["{}"]'.format(key)
                if key not in track_item:
                    track_item[key] = 0.0
                    track_item.keyframe_insert(keyframe_key, frame=0,
                                               group=midifile.name)
                item_offset = 0
                if msg.type == 'note_on':
                    value = msg.velocity
                else:
                    item_offset = -.01
                    value = 0.0
                track_item[key] = value
                track_item.keyframe_insert(keyframe_key, frame=(overall_offset_time + msg.time) * fps + item_offset,
                                           group=midifile.name)
        if counter == 0:  # this track doesn't contain note_on and/or note_off
            midifile.tracks.remove(midifile.tracks.find(track_item.name))

    if scene.animation_data and scene.animation_data.action:
        base_path = midifile.path_from_id('tracks')
        for fcurve in scene.animation_data.action.fcurves:
            if fcurve.data_path.startswith(base_path):
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'CONSTANT'
                # print(fcurve.data_path)