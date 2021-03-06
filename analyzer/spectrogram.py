import bpy

from .analyzer import Analyzer
from ..note_calculator import calculate_note


class SpectrogramGenerator(Analyzer):
    _driver = None

    def load(self, driver):
        self._driver = driver

    def stop(self):
        pass

    def on_pre_frame(self, scene, frame):
        if scene.audvis.spectrogram.enable:
            self.modify(scene)

    def modify(self, scene):
        name = 'AudVis Spectrogram'
        spect_props = scene.audvis.spectrogram
        height = spect_props.height
        if spect_props.mode == 'one-big':
            height = scene.frame_end - scene.frame_start + 1
        if name not in bpy.data.images:
            img = bpy.data.images.new(name=name, width=spect_props.width, height=height)
        else:
            img = bpy.data.images[name]
            if img.size[0] != spect_props.width or img.size[1] != height:
                img.scale(spect_props.width, height)
        mod = spect_props.skip_frames + 1
        if spect_props.skip_frames > 0 and (scene.frame_current_final - scene.frame_start) % mod != 0:
            return
        if spect_props.clear_on_first_frame and scene.frame_current_final == scene.frame_start:
            img.pixels = list(spect_props.color) * img.size[0] * img.size[1]
        width = img.size[0] * 4
        if spect_props.mode == 'one-big':
            line = scene.frame_current - scene.frame_start
            range_from = line * width
            range_to = line * width + width
        elif spect_props.mode == 'rolling':
            range_from = 0
            range_to = width
            img.pixels[width:] = img.pixels[:-width]
        rows_count = 1
        if spect_props.mode == 'snapshot':
            rows_count = height
            copy = [1.0] * (4 * width * height)
        else:
            copy = list(img.pixels[range_from:range_to])
        factor = spect_props.factor
        color = spect_props.color
        operation = spect_props.operation
        freq_step_calc = spect_props.freq_step_calc

        for i in range(0, width * rows_count, 4):
            freq_from = i / 4
            freq_from += spect_props.freqstart
            freq_from *= freq_step_calc
            val = calc_driver_value(spect_props, self._driver, int(i/4))
            if operation in ['sub', 'add']:
                if operation == 'sub':
                    val *= -1
                copy[i + 0] = color[0] + val * factor[0]
                copy[i + 1] = color[1] + val * factor[1]
                copy[i + 2] = color[2] + val * factor[2]
            elif operation == 'mul':
                copy[i + 0] = color[0] * val * factor[0]
                copy[i + 1] = color[1] * val * factor[1]
                copy[i + 2] = color[2] * val * factor[2]
            elif operation == 'set':
                copy[i + 0] = val * factor[0]
                copy[i + 1] = val * factor[1]
                copy[i + 2] = val * factor[2]
            copy[i + 3] = color[3]  # alpha channel
        if spect_props.mode == 'snapshot':
            img.pixels = copy
        else:
            img.pixels[range_from:range_to] = copy
        img.update()


# copy of analyzer/shapemodifier/lib.py - calc_driver_value
def calc_driver_value(settings, driver, index):
    if settings.freq_seq_type == 'notes':
        freq_from = calculate_note((index + settings.note_offset) * settings.note_step, settings.note_a4_freq)
        freq_to = calculate_note((index + settings.note_offset + 1) * settings.note_step, settings.note_a4_freq)
    elif settings.freq_seq_type == 'classic':
        rng = settings.freqrange
        freqstep = settings.freq_step_calc
        freqstart = settings.freqstart
        freq_from = index * freqstep + freqstart
        freq_to = index * freqstep + rng + freqstart

    if settings.freq_seq_type == 'midi':
        driver_value = driver(midi=index + settings.midi.offset,
                              ch=settings.midi.channel,
                              track=settings.midi.track,
                              file=settings.midi.file,
                              device=settings.midi.device) / 12.7
    else:
        send_kwargs = {}
        if settings.sound_sequence != '':
            send_kwargs['seq'] = settings.sound_sequence
        driver_value = driver(freq_from, freq_to, ch=settings.channel, **send_kwargs)
    return driver_value
