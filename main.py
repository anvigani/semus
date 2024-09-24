import numpy as np
import time
import os
import fluidsynth
from collections.abc import Iterable
from abc import ABCMeta, abstractmethod
from abc import ABC, abstractmethod
from collections import OrderedDict
from threading import Thread

import math
import numbers 
from numbers import Rational
import re
import logging
from enum import Enum
from fractions import Fraction
import xml.etree.ElementTree as ElementTree

from mido import MidiFile, MidiTrack, Message
from mido.midifiles import MetaMessage

fs = fluidsynth.Synth()
fs.start(driver = 'coreaudio')            

sfid = fs.sfload(r'/Applications/Soundfont/FluidR3_GM/FluidR3_GM.sf2') # Cambiare nel path proprio
fs.program_select(0, sfid, 0, 0)

# ==============================================================================
class PNote():
    def __init__(self, pitch=60, dur=0.5, vel=127):
        self.pitch    = pitch
        self.durata   = dur
        self.velocity = vel
        
        if isinstance(self.pitch, Iterable):     # se accordo (array)
                for n in self.pitch:
                    fs.noteon(0, n, self.velocity)
                time.sleep(self.durata)
                for n in self.pitch: 
                    fs.noteoff(0, n)
        else:                                     # se nota
            if self.pitch == 0:                   # se pausa pitch = 0 
                time.sleep(self.durata)
            else:
                fs.noteon(0, self.pitch, self.velocity)
                time.sleep(self.durata)
                fs.noteoff(0, self.pitch)

class PSeq (Thread):
    def __init__(self, pitch=60, dur=0.5, vel=127):
        Thread.__init__(self)
        self.pitch = pitch
        self.dur   = dur
        self.vel   = vel

        
    def run(self):        
        if type(self.pitch) == int or type(self.pitch) == tuple:
            if type(self.dur) == list and type(self.vel) == list:      # pitch dur[] vel[] 
                for i in range(len(self.dur)):
                    PNote(self.pitch, self.dur[i], self.vel[i])   
            elif type(self.dur) == list and type(self.vel) == int:     # pitch dur[] vel
                for i in range(len(self.dur)):
                    PNote(self.pitch, self.dur[i], self.vel)
            elif type(self.dur) == float and type(self.vel) == list:   # pitch dur vel[]
                for i in range(len(self.vel)):
                    PNote(self.pitch, self.dur, self.vel[i])
                    
        elif type(self.pitch) == list:
            if type(self.dur) == float and type(self.vel) == list:     # pitch[] dur vel[] 
                for i in range(len(self.pitch)):
                    PNote(self.pitch[i], self.dur, self.vel[i])            
            elif type(self.dur) == list and type(self.vel) == list:    # pitch[] dur[] vel[] 
                for i in range(len(self.pitch)):
                    PNote(self.pitch[i], self.dur[i], self.vel[i])               
            elif type(self.dur) == list and type(self.vel) == int:     # pitch[] dur[] vel
                for i in range(len(self.pitch)):
                    PNote(self.pitch[i], self.dur[i], self.vel)
  
            elif type(self.dur) == float and type(self.vel) == int:    #pitch[] dur vel
                for i in range(len(self.pitch)):
                    PNote(self.pitch[i], self.dur, self.vel)
            else:
                ""
        else:
            print('Non è una sequenza')

# ==============================================================================
# ============================================================================== 5
# ==============================================================================

class BoundaryPolicy:
    """
    Enum class that defines the boundary conditions on intervals, leaving 4 options:
        (a, b): Open
        [a, b]: Closed
        (a, b]: Low boundary open only
        [a, b): High boundary open only
    """
    Open, Closed, LO_Open, HI_Open = range(4)
    # Open,             (a, b)
    # Closed,           [a,b]
    # LO_OPEN,          (a, b]
    # HI_OPEN           [a, b)
    
    def __init__(self, itype):
        self.value = itype
        
    def __str__(self):
        if self.value == BoundaryPolicy.Open:
            return 'Open'
        if self.value == BoundaryPolicy.Closed:
            return 'Closed'
        if self.value == BoundaryPolicy.LO_Open:
            return 'LO_Open'
        if self.value == BoundaryPolicy.HI_Open:
            return 'HI_Open'
        
    def __eq__(self, y):
        return self.value == y.value
    
    def __hash__(self):
        return self.__str__().__hash__()
  
# ==============================================================================
class Interval(object):
    """
    Class defining an interval in the sense of real numbers defining a contiguous segment.
    """

    def __init__(self, lower, upper, policy=BoundaryPolicy.HI_Open):
        """
        Constructor.
        Args:
          lower: Rational or float, lower bound
          upper: Rational or float, upper bound
          policy: BoundaryPolicy defining endpoint constraints.
        """
        if lower > upper:
            raise Exception('Cannot specify Interval with lower > upper ({0} > {1})', lower, upper)
        
        self.__lower = lower
        self.__upper = upper
        self.__policy = policy
        
    @property
    def lower(self):
        return self.__lower
    
    @property
    def upper(self):
        return self.__upper
    
    @property
    def policy(self):
        return self.__policy

    def length(self):
        return self.upper - self.lower
    
    def contains(self, value):
        """
        Method to see of a rational value in contained in this interval.
        
        Args:
          value: Rational
        Returns: Boolean indicating if in boundary.
        """
        if self.policy == BoundaryPolicy.Open:
            return self.upper > value > self.lower
        if self.policy == BoundaryPolicy.Closed:
            return self.upper >= value >= self.lower
        if self.policy == BoundaryPolicy.LO_Open:
            return self.upper >= value > self.lower
        if self.policy == BoundaryPolicy.HI_Open:
            return self.upper > value >= self.lower
        
    @staticmethod
    def intersects(i1, i2):
        """
        Static methods that indicates if two intervals intersect
        
        Args:
          i1: Interval
          i2: Interval
        Returns: Boolean
        """
        return i1.contains(i2.lower) or i2.contains(i1.lower)
    
    def intersection(self, interval):
        """
        Method to return the intersection (Interval) of self and a given interval.
        
        Args:
          interval: Interval
        Returns:
          Interval intersection of self and interval, or None if they do not intersect.
        """
        if not Interval.intersects(self, interval):
            return None
    
        lo = interval.lower if self.contains(interval.lower) else self.lower
        lo_policy = interval.policy if self.contains(interval.lower) else self.policy
    
        hi = interval.upper if self.contains(interval.upper) else self.upper
        hi_policy = interval.policy if self.contains(interval.upper) else self.policy

        if lo_policy == hi_policy:
            bp = lo_policy
        else:
            if lo_policy == BoundaryPolicy.Open or lo_policy == BoundaryPolicy.LO_Open:
                bp = BoundaryPolicy.LO_Open
            else:
                bp = BoundaryPolicy.HI_Open
    
        return Interval(lo, hi, bp)
    
    @staticmethod
    def intersect(i1, i2):
        """
        Method to compute intersection of two Intervals.
        
        Args:
          i1: Interval
          i2: Interval
        Returns: 
          Interval intersection of i1 and i2.
        """
        return i1.intersection(i2)
    
    def __eq__(self, other):
        if not other:
            return False
        if isinstance(other, self.__class__):
            return self.lower == other.lower and self.upper == other.upper and self.policy == other.policy
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)
  
    def __str__(self):
        if self.policy == BoundaryPolicy.Open:
            return '({0}, {1})'.format(self.lower, self.upper)
        if self.policy == BoundaryPolicy.Closed:
            return '[{0}, {1}]'.format(self.lower, self.upper)
        if self.policy == BoundaryPolicy.LO_Open:
            return '({0}, {1}]'.format(self.lower, self.upper)
        if self.policy == BoundaryPolicy.HI_Open:
            return '[{0}, {1})'.format(self.lower, self.upper)

# ==============================================================================
class IntervalInfo(object):
    """
    Class defining object to hold the direct association of an interval to some object value.
    """
    
    def __init__(self, interval, value, rb_node):
        """
        Constructor
        
        Args:
        interval: type Interval, interval of interest.
        value: object value associated with the interval.
        rb_node: for this information.
        """
        self.__interval = interval
        self.__value = value
        
        # Some may indicate this is inappropriate.  Actually this value should only be visible to
        # IntervalTree and RBNode.  It is the best way to facilitate a node deletion.  With this,
        # We pass IntervalInfo (as received by a query say) to a delete method which can delete the node directly.
        self.__rb_node = rb_node
    
    @property
    def interval(self):
        return self.__interval
    
    @property
    def value(self):
        return self.__value
    
    @property
    def rb_node(self):
        return self.__rb_node
    
    def __str__(self): 
        return "({0} : {1})".format(self.interval, self.value)

# ==============================================================================
class RBNode(object):
    """
    Defines an implementation of a node in an interval tree
    """
    Red, Black = range(2)

    def __init__(self, interval=None, value=None, interval_tree=None):
        """
        Constructor.

        Args:
            interval: coverage Interval
            value: value mapped to
            interval_tree: parent IntervalTree
        """
        self.__interval = interval
        self.__key = interval.lower if interval else None
        self.__value = value
      
        self.__min = interval.lower if interval else None
        self.__max = interval.upper if interval else None
        
        self.__color = RBNode.Black

        self.__parent = None
        
        self.interval_tree = interval_tree
        
        self.__id = 1 if self.interval_tree is None else self.interval_tree.gen_node_id()
        
        self.__nil = interval_tree.nil if interval_tree else None
        self.__left = self.nil
        self.__right = self.nil

    @property
    def interval(self):
        return self.__interval
    
    @property
    def key(self):
        return self.__key
    
    @key.setter
    def key(self, k):
        self.__key = k
    
    @property
    def value(self):
        return self.__value
    
    @property
    def min(self):
        return self.__min
    
    @property
    def max(self):
        return self.__max
    
    @property
    def color(self):
        return self.__color
    
    @color.setter
    def color(self, color):
        self.__color = color
    
    @property
    def left(self):
        return self.__left
    
    @left.setter
    def left(self, node):
        self.__left = node
    
    @property
    def right(self):
        return self.__right
    
    @right.setter
    def right(self, node):
        self.__right = node
               
    @property
    def parent(self):
        return self.__parent
    
    @parent.setter
    def parent(self, node):
        self.__parent = node
        
    @min.setter
    def min(self, newmin):
        self.__min = newmin
        
    @max.setter
    def max(self, newmax):
        self.__max = newmax
        
    @property
    def nil(self):
        return self.__nil
    
    @property
    def id(self):
        return self.__id
    
    def coverage(self):
        if self.min is None or self.max is None:
            return None
        return Interval(self.min, self.max)
    
    def query_point(self, index, answer):
        """
        Query for all intervals that intersect a point.
        
        Args:
          index: Number to be queried about
          answer: List to be filled with answers
          
        Returns:
          The answer list of IntervalInfo's
        """
        if self.interval.contains(index):
            answer.append(IntervalInfo(self.interval, self.value, self))
        if self.left != self.nil and self.left.max > index >= self.left.min:
            self.left.query_point(index,  answer)
        if self.right != self.nil and self.right.max > index >= self.right.min:
            self.right.query_point(index,  answer)
        return answer
            
    def query_interval(self, interval, answer):
        """
        Query for all intervals that intersect a given interval.
        
        Args:
          interval: The Interval to check intersection against
          answer:  The return list of IntervalInfo's
        
        Returns:
          The answer list of IntervalInfo's
        """
        if Interval.intersects(self.interval, interval):
            answer.append(IntervalInfo(self.interval, self.value, self))
        if self.left != self.nil and (self.left.min <= interval.upper and self.left.max > interval.lower): 
            self.left.query_interval(interval,  answer)

        if self.right != self.nil and (self.right.min <= interval.upper and self.right.max > interval.lower):
            self.right.query_interval(interval,  answer)
        return answer
    
    def query_interval_start(self, interval, answer):
        """
        Find all intervals that start in the given interval, and only those.
        
        Args:
          interval: The interval to collect interval starts on.
          answer: The return list of IntervalInfo's
          
        Returns:
          The answer list of IntervalInfo's
        """
        if interval.contains(self.interval.lower):
            answer.append(IntervalInfo(self.interval, self.value, self))
                       
        if self.left != self.nil and (self.left.min <= interval.upper and self.left.max > interval.lower): 
            self.left.query_interval_start(interval,  answer)

        if self.right != self.nil and (self.right.min <= interval.upper and self.right.max > interval.lower):
            self.right.query_interval_start(interval,  answer)
        return answer

    def intervals(self, interval_list):
        if self.left != self.nil:
            self.left.intervals(interval_list)
        interval_list.add(self.interval)
        if self.right != self.nil:
            self.right.intervals(interval_list)
        return interval_list
    
    def intervals_and_values(self, info_list):
        if self.left != self.nil:
            self.left.intervals_and_values(info_list)
     
        info_list.add(IntervalInfo(self.interval, self.value, self))
        if self.right != self.nil:
            self.right.intervals_and_values(info_list)
      
        return info_list
    
    def apply_update(self):
        x = self
        while x != self.nil:
            x.update_min_max()
            x = x.parent
            
    def update_min_max(self):
        maxx = self.interval.upper
        if self.left != self.nil:
            maxx = self.left.max if maxx < self.left.max else maxx
    
        if self.right != self.nil:
            maxx = self.right.max if maxx < self.right.max else maxx
     
        self.max = maxx
      
        minn = self.interval.lower
        if self.left != self.nil:
            minn = self.left.min if minn > self.left.min else minn

        if self.right != self.nil:
            minn = self.right.min if minn > self.right.min else minn
      
        self.min = minn
        
    def left_rotate(self):  # assumes x, swaps with x.right
        x = self
        y = x.right
        x.right = y.left
        if y.left != self.nil:
            y.left.parent = x
        y.parent = x.parent
        if x.parent == self.nil:
            self.interval_tree.root = y
        else:
            if x == x.parent.left:
                x.parent.left = y
            else:
                x.parent.right = y
      
        y.left = x
        x.parent = y
        self.apply_update()

    def right_rotate(self):  # assume y, swaps with y.left
        y = self
        x = y.left
        y.left = x.right
        if x.right != self.nil:
            x.right.parent = y

        x.parent = y.parent
        if y.parent == self.nil:
            self.interval_tree.root = x
        else:
            if y == y.parent.right:
                y.parent.right = x
            else:
                y.parent.left = x

        x.right = y
        y.parent = x
      
        self.apply_update()
        
    def node_minimum(self):
        x = self
        while self.left != self.nil:
            x = self.left()
        return x
    
    def node_maximum(self):
        x = self
        while self.right != self.nil:
            x = self.right()
        return x
    
    def node_successor(self):
        if self.right != self.nil:
            return self.right.node_minimum()
        y = self.parent
        x = self
        while y != self.nil and x == y.right:
            x = y
            y = y.parent
        return y   
            
    def delete_node(self, rb_node):
        """
        Best description is in Cormen ( p. 251):
        
        The procedure for deleting a given node z from a binary search tree takes as an argument a pointer to z.
        The procedure considers the three cases shown in Figure 13.4.  If z has no children, we modify its parent p[z]
        to replace z with NIL as its child.  If the node has only a single child, we "splice out" z by making a 
        new link between its child and its parent.  Finally, if the node has two children,
        we splice out z's successor y,
        which has no left child ... and replace the contents of z with the contents of y. 
        
        In order to key prior search results valid (ref. IntervalInfo), we ALWAYS want to get rid of z.  So in the third
        case, we really want to replace rb_node with its successor, moving left, right from rb_node to the successor and
        re-assigning the parentage.
        """
        if rb_node.left == self.nil or rb_node.right == self.nil:
            x = rb_node.left if rb_node.left != self.nil else rb_node.right
            x.parent = rb_node.parent
            if rb_node.parent == self.nil:
                self.interval_tree.root = x
            else:
                if rb_node == rb_node.parent.left:
                    rb_node.parent.left = x
                else:
                    rb_node.parent.right = x
            # Please test to see if this fixes spans
            if rb_node.parent != self.nil:
                rb_node.parent.apply_update()
            if x != self.nil and rb_node.color == RBNode.Black:
                self._rb_delete_fixup(x)
        else:
            y = rb_node.node_successor()
            x = y.left if y.left != self.nil else y.right 
            if x != self.nil:
                x.parent = y.parent if y.parent != rb_node else y
            if y.parent == self.nil:
                self.interval_tree.root = x
            else:
                if y.parent != rb_node:
                    if y == y.parent.left:
                        y.parent.left = x
                    else:
                        y.parent.right = x  
                    
            # replace rb_node with y
            
            y.left = rb_node.left 
            if y.left != self.nil:
                y.left.parent = y
            y.right = rb_node.right if y.parent != rb_node else y.right
            if y.right != self.nil:
                y.right.parent = y
            y.color = rb_node.color
            y.parent = rb_node.parent
            if rb_node.parent == self.nil:
                self.interval_tree.root = y
            else:
                if rb_node == rb_node.parent.left:
                    rb_node.parent.left = y
                else:
                    rb_node.parent.right = y
            # Please test to see if this fixes spans
            # I think the span for y should be computed immediately, then y.apply_update()
            if y != self.nil:
                y.apply_update()
            if y.color == RBNode.Black and x != self.nil:
                self._rb_delete_fixup(x)    

    def _rb_delete_fixup(self, x):
        while x != self.interval_tree.root and x.color == RBNode.Black:
            if x == x.parent.left:
                w = x.parent.right
                if w.color == RBNode.Red:
                    w.color = RBNode.Black
                    x.parent.color = RBNode.Red
                    x.parent.left_rotate() 
                    w = x.parent.right
                if w.left.color == RBNode.Black and w.right.color == RBNode.Black:
                    w.color = RBNode.Red
                else:
                    if w.right.color == RBNode.Black:
                        w.left.color = RBNode.Black
                        w.color = RBNode.Red
                        w.right_rotate()
                    w.color = x.parent.color
                    x.parent.color = RBNode.Black
                    w.right.color = RBNode.Black
                    x.parent.left_rotate()
                    x = self.interval_tree.root
            else:
                w = x.parent.left
                if w.color == RBNode.Red:
                    w.color = RBNode.Black
                    x.parent.color = RBNode.Red
                    x.parent.right_rotate() 
                    w = x.parent.left
                if w.right.color == RBNode.Black and w.left.color == RBNode.Black:
                    w.color = RBNode.Red
                else:
                    if w.left.color == RBNode.Black:
                        w.right.color = RBNode.Black
                        w.color = RBNode.Red
                        w.left_rotate()
                    w.color = x.parent.color
                    x.parent.color = RBNode.Black
                    w.left.color = RBNode.Black
                    x.parent.right_rotate()
                    x = self.interval_tree.root

        x.color = RBNode.Black      
        
    def print_tree(self):
        s = ''
        if self.left != self.nil:
            s = s + self.left.print_tree()   # self.left.print_tree()

        s = s + str(self) + '\n'
      
        if self.right != self.nil:
            s = s + self.right.print_tree()  # self.right.print_tree();
        return s
    
    def __str__(self): 
        return "[{0}] key={1} interval={2} c={3} parent=[{4}] span=[{5}, {6}] --> [{7}, {8}]".format(
          self.id, self.key, self.interval, 'B' if self.color == RBNode.Black else 'R',
          self.parent.id, self.min, self.max,
          'null' if self.left is None else self.left.id,
          'null' if self.right is None else self.right.id)

# ==============================================================================
class ChromaticScale(object):

    NUMBER_OF_SEMITONES = 12
    CHROMATIC_START = (0, 9)
    CHROMATIC_END = (8, 0)

    A0 = 27.5000    # lowest chromatic frequency in chromatic scale, corresponds to (0, 9) or '0:9'
    SEMITONE_RATIO = math.pow(2.0, 1.0 / 12.0)

    # (partition number, 12-based offset)
    CHROMATIC_FORM = r'([0-8]):(10|11|[0-9])' 
    CHROMATIC_PATTERN = re.compile(CHROMATIC_FORM)

    @staticmethod
    def get_chromatic_scale(start_pitch, end_pitch):
        """
        Get the chromatic scale from start to end inclusive.
    
        Args
            start: chromatic location of starting pitch (p, i) 
            end: chromatic location of ending pitch (p, i)
        Returns
            List of semitone frequencies from start to end inclusive.
        """
    
        start_index = ChromaticScale.location_to_index(start_pitch)
        end_index = ChromaticScale.location_to_index(end_pitch)
    
        if start_index > end_index:
            return None
    
        if start_index < ChromaticScale.location_to_index(ChromaticScale.CHROMATIC_START) or \
           end_index > ChromaticScale.location_to_index(ChromaticScale.CHROMATIC_END):
            return None
    
        freq = ChromaticScale.A0
        for _ in range(ChromaticScale.location_to_index(ChromaticScale.CHROMATIC_START) + 1, start_index + 1):
            freq *= ChromaticScale.SEMITONE_RATIO
        
        answer = [freq]
        for _ in range(start_index + 1, end_index + 1):
            freq *= ChromaticScale.SEMITONE_RATIO
            answer.append(freq)
        return answer 

    @staticmethod
    def get_frequency(pitch_location):
        """
        Get the frequency for a given pitch as chromatic location.
        
        Args:
            pitch_location: in (p, i) form
        Returns:
            frequency: (float)
        """
        index = ChromaticScale.location_to_index(pitch_location) 
    
        if index < ChromaticScale.location_to_index(ChromaticScale.CHROMATIC_START) or \
           index > ChromaticScale.location_to_index(ChromaticScale.CHROMATIC_END):
            return None 
    
        freq = ChromaticScale.A0
        for _ in range(ChromaticScale.location_to_index(ChromaticScale.CHROMATIC_START) + 1, index + 1):
            freq *= ChromaticScale.SEMITONE_RATIO
        
        return freq

    @staticmethod
    def parse_notation(notation):
        """"
        Parse a pitch in 'o:i' string format into (0, i) form.
        
        Args:
            notation: pitch in 'o:i' format
        Returns:
            pitch in (o, i) form
        """
        n = ChromaticScale.CHROMATIC_PATTERN.match(notation)
        if not n:
            return None
        return int(n.group(1)), int(n.group(2))

    @staticmethod
    def location_to_index(pitch):
        """
        Convert a pitch in (p, i) form into absolute index
        
        Args:
            pitch: in (p, i) form
        Return:
            corresponding absolute index of (o, i) form
        """
        return ChromaticScale.NUMBER_OF_SEMITONES * pitch[0] + pitch[1]

    @staticmethod
    def index_to_location(index):
        """
        Convert pitch absolute index to (p, i) form
        
        Args:
            absolute index of pitch
        Returns:
            (o, i) form of absolute index
        """
        return index // ChromaticScale.NUMBER_OF_SEMITONES, index % ChromaticScale.NUMBER_OF_SEMITONES
    
    @staticmethod
    def chromatic_start_index():
        return ChromaticScale.location_to_index(ChromaticScale.CHROMATIC_START)
    
    @staticmethod
    def chromatic_end_index():
        return ChromaticScale.location_to_index(ChromaticScale.CHROMATIC_END)
    
# ==============================================================================
class DiatonicToneCache(object):

    DIATONIC_CACHE = None

    def __init__(self):
        """
        Constructor.
        
        Args: None
          
        """
        
        #  map tone name to tone.
        self.diatonic_map = {}
        
        self.__build_diatonics()
        
    @staticmethod
    def get_cache():
        if DiatonicToneCache.DIATONIC_CACHE is None:
            DiatonicToneCache.DIATONIC_CACHE = DiatonicToneCache()
        return DiatonicToneCache.DIATONIC_CACHE

    @staticmethod        
    def get_tone(tone_text):
        cache = DiatonicToneCache.get_cache()
        return cache.get_cache_tone(tone_text)
    
    @staticmethod
    def get_tones():
        cache = DiatonicToneCache.get_cache()
        tones = []
        for ltr in DiatonicTone.DIATONIC_LETTERS:
            for aug in DiatonicTone.AUGMENTATIONS:
                tones.append(cache.get_cache_tone(ltr + aug))
        return tones
    
    def get_cache_tone(self, tone_text):            
        return self.diatonic_map[tone_text.lower()]           

    def __build_diatonics(self):
        """
        Builds all diatonic tones for the cache.
        """
        for ltr in DiatonicTone.DIATONIC_LETTERS:
            for aug in DiatonicTone.AUGMENTATIONS:
                self.diatonic_map[(ltr + aug).lower()] = DiatonicTone(ltr + aug) 

# ==============================================================================
class DiatonicTone(object):
    
    # Basic diatonic tone letters.
    DIATONIC_LETTERS = list('CDEFGAB')
    
    # Regex used for parsing diatonic pitch.
    DIATONIC_PATTERN_STRING = '([A-Ga-g])(bbb|bb|b|###|##|#)?'
    DIATONIC_PATTERN = re.compile(DIATONIC_PATTERN_STRING)
    
    # Diatonic C scale indices
    DIATONIC_INDEX_MAPPING = {'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6}
    # Semitone offsets for all diatonic pitch letters
    CHROMATIC_OFFSETS = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    
    # All augmentations in text representation
    AUGMENTATIONS = ('bbb', 'bb', 'b', '', '#', '##', '###')
    AUGMENTATION_OFFSET_MAPPING = {'': 0, 'b': -1, 'bb': -2, 'bbb': -3, '#': 1, '##': 2, '###': 3}

    DIATONIC_OFFSET_ENHARMONIC_MAPPING = {
        0: ['C', 'B#', 'Dbb'],
        1: ['C#', 'B##', 'Db'],
        2: ['D', 'C##', 'Ebb'],
        3: ['D#', 'Eb', 'Fbb'],
        4: ['E', 'D##', 'Fb'],
        5: ['F', 'E#', 'Gbb'],
        6: ['F#', 'E##', 'Gb'],
        7: ['G', 'F##', 'Abb'],
        8: ['G#', 'Ab'],
        9: ['A', 'G##', 'Bbb'],
        10: ['A#', 'Bb', 'Cbb'],
        11: ['B', 'A##', 'Cb']
        }

    def __init__(self, diatonic_name):
        """
        Constructor

        Args:
            diatonic_name: Textual name of the tone.
        """
        diatonic_info = DiatonicTone.parse(diatonic_name)
        if not diatonic_info:
            raise Exception('Illegal diatonic pitch specified {0}'.format(diatonic_name)) 
        
        self.__diatonic_letter = diatonic_info[0]
        self.__augmentation_symbol = diatonic_info[1]
        self.__diatonic_symbol = self.diatonic_letter + self.augmentation_symbol
        
        # diatonic tone offset from C within one octave.
        self.__diatonic_index = DiatonicTone.DIATONIC_INDEX_MAPPING[diatonic_info[0]]

        self.__augmentation_offset = DiatonicTone.AUGMENTATION_OFFSET_MAPPING[self.augmentation_symbol]
        # Full offset from beginning of chromatic partition, this is not the same as placement.
        # Note; This can be < 0 or > 11, , Cb is -1, and B# is 12
        # Note that in DiatonicPitch, this provides the accurate adjustment of chromatic partition (octave) number.
        self.__tonal_offset = DiatonicTone.CHROMATIC_OFFSETS[self.diatonic_letter] + self.augmentation_offset
        
        # This is the absolute tone regardless of chromatic partition, e.g.Cb is 11 or B; B# is 0 or C. 
        self.__placement = (self.tonal_offset if self.tonal_offset >= 0 else self.tonal_offset + 12) % 12
        
    @property
    def diatonic_letter(self):
        return self.__diatonic_letter
    
    @property
    def diatonic_symbol(self):
        return self.__diatonic_symbol
    
    @property
    def augmentation_symbol(self):
        return self.__augmentation_symbol
    
    @property
    def diatonic_index(self):
        return self.__diatonic_index
    
    @property
    def augmentation_offset(self):
        return self.__augmentation_offset
    
    @property
    def tonal_offset(self):
        return self.__tonal_offset
    
    @property
    def placement(self):
        return self.__placement    
    
    def __str__(self):
        return '{0}({1}, {2}, {3}, {4})'.format(self.diatonic_symbol,
                                                self.diatonic_index, self.diatonic_index,
                                                self.tonal_offset, self.augmentation_offset)
    
    def __eq__(self, other):
        if other is None or not isinstance(other, DiatonicTone):
            return False
        return self.diatonic_symbol == other.diatonic_symbol
    
    def __hash__(self):
        return self.diatonic_symbol.__hash__()
    
    def enharmonics(self):
        """
        For this tone, provide a list of enharmonic equivalents.
        
        Args: none
        Return: List of enharmonic diatonic tone names
        """
        offset = self.tonal_offset
        if offset < 0:
            offset += 12
        if offset >= 12:
            offset %= 12
            
        return DiatonicTone.DIATONIC_OFFSET_ENHARMONIC_MAPPING[offset]
     
    @staticmethod
    def enharmonics_for(diatonic_tone):
        """
        Get the enharmonics for a given tone [given as text].
        
        Args:
          diatonic_tone: text represention of diatonic tone.
          
        Return: 
          List of enharmonic diatonic tone names.
        """
        return DiatonicTone(diatonic_tone).enharmonics()    
    
    @staticmethod 
    def get_diatonic_letter(index):
        """
        Get the diatonic letter based in integer index.

        :param index:
        :return:
        """
        return DiatonicTone.DIATONIC_LETTERS[index]  
    
    @staticmethod
    def augmentation(augmentation_dist):
        """
        Get the augmentation symbol based on index based on offset, e.g. _2, _1, 0, 1, 2.

        :param augmentation_dist:
        :return:
        """
        return DiatonicTone.AUGMENTATIONS[augmentation_dist + 3] 
    
    @staticmethod
    def alter_tone_by_augmentation(tone, augmentation_delta):
        """
        Given a tone and a (int) change in augmentation, find the resulting DiatonicTone
        
        Args:
          tone: DiatonicTone
          augmentation_delta: (int) amount of change in augmentation.
          
        Returns:
          DiatonicTone for the altered tone.
        """

        basic_symbol = tone.diatonic_letter
        augmentation = tone.augmentation_offset + augmentation_delta
        basic_symbol, augmentation = DiatonicTone.enharmonic_adjust(basic_symbol, augmentation)
        aug_symbol = DiatonicTone.augmentation(augmentation)
        return DiatonicToneCache.get_cache().get_tone(basic_symbol + aug_symbol)

    LTRS = 'CDEFGAB'
    POS_INC = [2, 2, 1, 2, 2, 2, 1]
    NEG_INC = [-1, -2, -2, -1, -2, -2, -2]

    @staticmethod
    def enharmonic_adjust(ltr, augmentation):
        """
        In some cases, symbols like G#### or Abbbbb might come up. This is a check for those rare cases, so
        that enharmonic equivalents can be accessed.
        :param ltr:
        :param augmentation:
        :return:
        """

        if abs(augmentation) <= 3:
            return ltr, augmentation
        if augmentation > 0:
            while augmentation > 2:
                i = DiatonicTone.LTRS.index(ltr.upper())
                augmentation -= DiatonicTone.POS_INC[i]
                ltr = DiatonicTone.LTRS[i + 1] if i < 6 else DiatonicTone.LTRS[0]
        else:
            while augmentation < -2:
                i = DiatonicTone.LTRS.index(ltr.upper())
                augmentation -= DiatonicTone.NEG_INC[i]
                ltr = DiatonicTone.LTRS[i - 1] if i > 0 else DiatonicTone.LTRS[6]
        return ltr, augmentation

    @staticmethod   
    def parse(diatonic_tone_text):
        """
        Parse a textual representation of diatonic pitch
        
        Args:
          diatonic_tone_text: text representation of diatonic tone.
          
        Returns:
          (letter part upper case, augmentation text)  if no augmentation, return '' for augmentation
        """
        if not diatonic_tone_text:
            return None
        m = DiatonicTone.DIATONIC_PATTERN.match(diatonic_tone_text)
        if not m:
            return None
        return m.group(1).upper(), '' if m.group(2) is None else m.group(2)

    @staticmethod
    def to_upper(diatonic_tone_text):
        parts = DiatonicTone.parse(diatonic_tone_text)
        if parts is None:
            return None
        return parts[0] + parts[1]

    @staticmethod
    def calculate_diatonic_distance(tone1, tone2):
        """
        Diatonic count from tone1 to tone2 (upwards)
        :rtype: integer
        :param tone1:
        :param tone2:
        :return: int diatonic count from tone1 to tone2 which is always positive.
        """
        return (tone2.diatonic_index - tone1.diatonic_index) % 7
    
# ==============================================================================
class DiatonicFoundation(object):
    
    # Map all valid tones to their displacement on chromatic partition.
    TONE_PLACEMENT = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11,
                      'Cb': -1, 'Db': 1, 'Eb': 3, 'Fb': 4, 'Gb': 6, 'Ab': 8, 'Bb': 10,
                      'C#': 1, 'D#': 3, 'E#': 5, 'F#': 6, 'G#': 8, 'A#': 10, 'B#': 12,
                      'Cbb': -2, 'Dbb': 0, 'Ebb': 2, 'Fbb': 3, 'Gbb': 5, 'Abb': 7, 'Bbb': 9,
                      'C##': 2, 'D##': 4, 'E##': 6, 'F##': 8, 'G##': 9, 'A##': 11, 'B##': 13,
                      }
    
    # Note: this needs to sync with DiatonicTone.DIATONIC_OFFSET_ENHARMONIC_MAPPING
    ENHARMONIC_OCTAVE_ADJUSTMENT_MAPPING = {
        0: [0, -1, 0],
        1: [0, -1, 0],
        2: [0, 0, 0],
        3: [0, 0, 0],
        4: [0, 0, 0],
        5: [0, 0, 0],
        6: [0, 0, 0],
        7: [0, 0, 0],
        8: [0, 0],
        9: [0, 0, 0],
        10: [0, 0, 1],
        11: [0, 0, 1]
        }

    def __init__(self):
        """
        Constructor
        """
    
    @staticmethod 
    def get_chromatic_distance(diatonic_pitch):
        """
        Convert a diatonic pitch into its chromatic distance
        
        Args:
          diatonic_pitch: instance of DiatonicPitch
        Return:
          the chromatic index of the pitch, e.g. 48 for C4.
        """
        return diatonic_pitch.chromatic_distance
    
    @staticmethod 
    def map_to_diatonic_scale(chromatic_index):
        """
        Convert a chromatic index (int) to a diatonic pitch in string format.
        
        Args:
          chromatic_index: the chromatic index of the pitch (int)
        Return:
          all enharmonic diatonic pitches
        """

        location = ChromaticScale.index_to_location(chromatic_index)
        enharmonics = DiatonicTone.DIATONIC_OFFSET_ENHARMONIC_MAPPING[location[1]]
        octave_adjustments = DiatonicFoundation.ENHARMONIC_OCTAVE_ADJUSTMENT_MAPPING[location[1]]
        answers = []
        for i in range(0, len(enharmonics)):
            enharmonic = enharmonics[i]
            answers.append(DiatonicPitch.parse(enharmonic + ':' + str(location[0] + octave_adjustments[i])))
        return answers
    
    @staticmethod        
    def add_semitones(diatonic_pitch, semitones):
        """
        Given a diatonic pitch, add a number of semitones, and return
          all enharmonic representations.
          
        Args:
          diatonic_pitch: DiatonicPitch instance
          semitones: number of semitones to add
        Returns:
          A list of enharmonic quivalent pitches that result from the addition.
        """
        index = DiatonicFoundation.get_chromatic_distance(diatonic_pitch)
        if index == -1:
            return None
        return DiatonicFoundation.map_to_diatonic_scale(index + semitones)
    
    @staticmethod
    def semitone_difference(diatonic_pitch_a, diatonic_pitch_b):
        """
        Given two pitches, compute their difference, 1st - 2nd
        
        Args:
          diatonic_pitch_a: DiatonicPitch instance
          diatonic_pitch_b: DiatonicPitch instance
        Returns:
          1st - 2nd returning semitones.
        """
        index_a = DiatonicFoundation.get_chromatic_distance(diatonic_pitch_a)
        index_b = DiatonicFoundation.get_chromatic_distance(diatonic_pitch_b)
        if index_a == -1 or index_b == -1:
            raise Exception('Illegal pitch specified')
        return index_a - index_b
                
    @staticmethod
    def get_tone(diatonic_tone_text):
        """
        Fetch a cached diatonic tone based on text representation.
        
        Args:
          diatonic_tone_text: text specification, e.g. Abb
          
        Returns:
          DiatonicTone for specified pitch
          
        Exceptions:
          If specified pitch cannot be parsed.
        """
        return DiatonicToneCache.get_tone(diatonic_tone_text)
    
    @staticmethod
    def get_tones():
        return DiatonicToneCache.get_tones()

# ==============================================================================
class DiatonicPitch(object):
    """
    Class that encapuslates the idea of a diatonic pitch along with its position on 
      tonal scale.  That is it takes an octave plus a diatonic tone.
      
      Class properties:
      octave:  The octave for this pitch
      diatonic_tone:  The DiatonicTone for this pitch
    """
    
    # Regex used for parsing diatonic pitch.
    DIATONIC_PATTERN = re.compile(r'([A-Ga-g])(bbb|bb|b|###|##|#)?:?([0-8])')

    def __init__(self, octave, diatonic_tone):
        """
        Constructor
      
        Args:
          octave:  integer >=0
          diatonic_tone: tone or letter representation of the diatonic tone, e.g. D#
          
          Note: 
            The tone is relative to the partition based on tonal_offset.  
            So, Cb:4 is really B:3 - however we retain 4 as the partition as Cb is relative to the 4th.
                Same with B#4 which is really C:5, we retain the 4.
            So the partition is not the actual partition, but the relative partition number.
        """
        self.__octave = octave
        
        if isinstance(diatonic_tone, DiatonicTone):
            self.__diatonic_tone = diatonic_tone
        else:
            self.__diatonic_tone = DiatonicFoundation.get_tone(diatonic_tone)
        self.__chromatic_distance = 12 * octave + self.diatonic_tone.tonal_offset
    
    @property
    def octave(self):
        return self.__octave
    
    @property
    def diatonic_tone(self):
        return self.__diatonic_tone
    
    @property
    def chromatic_distance(self):
        return self.__chromatic_distance

    def enharmonics(self):
        return DiatonicFoundation.map_to_diatonic_scale(self.chromatic_distance)
    
    def diatonic_distance(self):
        """
        Note letter distance on the diatonic scale.
        """
        return self.octave * 7 + self.diatonic_tone.diatonic_index
    
    def __str__(self):
        return '{0}:{1}'.format(self.diatonic_tone.diatonic_symbol, self.octave)
    
    def __eq__(self, other):
        if other is None or not isinstance(other, DiatonicPitch):
            return False
        return self.octave == other.octave and self.diatonic_tone == other.diatonic_tone
    
    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if other is None:
            return False
        return self.chromatic_distance < other.chromatic_distance

    def __le__(self, other):
        if other is None:
            return False
        if self.__eq__(other):
            return True
        return self.__lt__(other)
    
    def __hash__(self):
        return self.__str__().__hash__()
    
    @staticmethod   
    def parse(diatonic_pitch_text):
        """
        Parse a textual representation of diatonic pitch
        
        Args:
          diatonic_pitch_text: text representation of diatonic pitch;
          
        Returns:
          (diatonic_tone, octave)
        """
        if not diatonic_pitch_text:
            return None
        m = DiatonicPitch.DIATONIC_PATTERN.match(diatonic_pitch_text)
        if not m:
            return None
        diatonic_tone = DiatonicToneCache.get_tone(m.group(1).upper() + ('' if m.group(2) is None else m.group(2)))
        if not diatonic_tone:
            return None

        return DiatonicPitch(0 if m.group(3) is None else int(m.group(3)), diatonic_tone)

    LTRS = 'CDEFGAB'

    @staticmethod
    def crosses_c(t1, t2, up_down=True):
        """
        Utility method to determine if two tones (within octave) cross C, implying a different octaves.
        :param t1: 
        :param t2: 
        :param up_down: t1 goes to t2 either in increasing (True) or decreasing (False) manner.
        :return: 
        """
        ltr = t1.diatonic_letter.upper() if isinstance(t1, DiatonicTone) else t1.upper()
        i1 = DiatonicPitch.LTRS.index(ltr)
        ltr = t2.diatonic_letter.upper() if isinstance(t2, DiatonicTone) else t2.upper()
        i2 = DiatonicPitch.LTRS.index(ltr)
        if i1 == i2:
            return False
        return up_down if i1 > i2 else not up_down
    

# ==============================================================================
# ============================================================================== 6
# ==============================================================================

class IntervalException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

# ==============================================================================
class IntervalType(Enum):
    """
    Enum class for the quality of musical intervals.
    """
    Major = 1
    Minor = 2
    Diminished = 3
    Augmented = 4
    Perfect = 5

    @staticmethod
    def short_notation(t):
        if t == IntervalType.Major:
            return "M"
        elif t == IntervalType.Minor:
            return "m"
        elif t == IntervalType.Diminished:
            return "d"
        elif t == IntervalType.Augmented:
            return "A"
        elif t == IntervalType.Perfect:
            return "P"
        raise Exception('Invalid interval key {0}.'.format(t))

    def __str__(self):
        return self.name

# ==============================================================================
class IntervalN(object):
    """
    Class that encapsulates the notions of a musical interval.
    An interval is a diatonic measure of distance between two diatonic pitches.  It is qualified by two attributes
    1) The number of letter steps between the two pitches
    2) A qualitative characterization of the sound of the distance, as given by IntervalType
    
    We strictly enforce that the starting pitch must precede the end pitch. 
    """
    
    # mapping (diatonic-distance, semitone distance) --> IntervalType
    #   Note:  We are excluding 'diminished unison', as it causes consistency issues, and is controversial.
    #          Although 'augmented octave' is valid in itself, due to the above, it's inversion is illegal.
    INTERVAL_MAP = {
        (0, -1): IntervalType.Diminished,
        (0, 0): IntervalType.Perfect,
        (0, 1): IntervalType.Augmented,
        (1, 0): IntervalType.Diminished,
        (1, 1): IntervalType.Minor,
        (1, 2): IntervalType.Major,
        (1, 3): IntervalType.Augmented,
        (2, 2): IntervalType.Diminished,
        (2, 3): IntervalType.Minor,
        (2, 4): IntervalType.Major,
        (2, 5): IntervalType.Augmented,
        (3, 4): IntervalType.Diminished,
        (3, 5): IntervalType.Perfect,
        (3, 6): IntervalType.Augmented,
        (4, 6): IntervalType.Diminished,
        (4, 7): IntervalType.Perfect,
        (4, 8): IntervalType.Augmented,
        (5, 7): IntervalType.Diminished,
        (5, 8): IntervalType.Minor,
        (5, 9): IntervalType.Major,
        (5, 10): IntervalType.Augmented,
        (6, 9):  IntervalType.Diminished,
        (6, 10): IntervalType.Minor,
        (6, 11): IntervalType.Major,
        (6, 12): IntervalType.Augmented,
        (7, 11): IntervalType.Diminished,
        (7, 12): IntervalType.Perfect,
        (7, 13): IntervalType.Augmented,
    }
    
    INVERSE_INTERVAL_MAP = {(v, k[0]): k[1] for k, v in INTERVAL_MAP.items()}
    
    INTERVAL_AVAILABLE_TYPES = {
            1: {-1: IntervalType.Diminished, 0: IntervalType.Perfect, 1: IntervalType.Augmented},
            2: {-2: IntervalType.Diminished, -1: IntervalType.Minor, 0: IntervalType.Major, 1: IntervalType.Augmented},
            3: {-2: IntervalType.Diminished, -1: IntervalType.Minor, 0: IntervalType.Major, 1: IntervalType.Augmented},
            4: {-1: IntervalType.Diminished, 0: IntervalType.Perfect, 1: IntervalType.Augmented},
            5: {-1: IntervalType.Diminished, 0: IntervalType.Perfect, 1: IntervalType.Augmented},
            6: {-2: IntervalType.Diminished, -1: IntervalType.Minor, 0: IntervalType.Major, 1: IntervalType.Augmented},
            7: {-2: IntervalType.Diminished, -1: IntervalType.Minor, 0: IntervalType.Major, 1: IntervalType.Augmented},
    }
    
    VALID_INTERVALS = {
        (0, IntervalType.Diminished),
        (0, IntervalType.Perfect),
        (0, IntervalType.Augmented),
        (1, IntervalType.Diminished),
        (1, IntervalType.Minor),
        (1, IntervalType.Major),
        (1, IntervalType.Augmented),
        (2, IntervalType.Diminished),
        (2, IntervalType.Minor),
        (2, IntervalType.Major),
        (2, IntervalType.Augmented),
        (3, IntervalType.Diminished),
        (3, IntervalType.Perfect),
        (3, IntervalType.Augmented),
        (4, IntervalType.Diminished),
        (4, IntervalType.Perfect),
        (4, IntervalType.Augmented),
        (5, IntervalType.Diminished),
        (5, IntervalType.Minor),
        (5, IntervalType.Major),
        (5, IntervalType.Augmented),
        (6, IntervalType.Diminished),
        (6, IntervalType.Minor),
        (6, IntervalType.Major),
        (6, IntervalType.Augmented),
        (7, IntervalType.Diminished),
        (7, IntervalType.Perfect),
        (7, IntervalType.Augmented),
    }

    def __init__(self, diatonic_distance, interval_type):
        """
        Constructor
        
        Args:
          diatonic_distance: number of diatonic tones, 'cdefgab', covered by the interval (inclusive), origin 1
          interval_type: see class IntervalType, or one of the values IntervalType.Major, ...
        """
        if isinstance(interval_type, int):
            interval_type = IntervalType(interval_type)
        self.__interval_type = interval_type
        
        self.__diatonic_distance = (abs(diatonic_distance) - 1) * IntervalN._sign(diatonic_distance)
        
        octave = IntervalN._compute_octave(self.__diatonic_distance) 
        
        d_d = abs(self.__diatonic_distance - 7 * octave)
                   
        key = (d_d, interval_type)
        if key not in IntervalN.VALID_INTERVALS:
            raise Exception('Illegal Interval for {0}-{1}'.format(diatonic_distance, self.interval_type)) 
         
        self.__chromatic_distance = IntervalN._sign(self.__diatonic_distance) * \
            (IntervalN.INVERSE_INTERVAL_MAP[(self.interval_type, d_d)]) + 12 * octave
        
    @staticmethod
    def create_interval(pitch_a, pitch_b):
        """
        Create an interval based on two diatonic pitches.
        
        Args:
          pitch_a: the lower diatonic pitch
          pitch_b: the upper diatonic pitch
        Returns:
          the resulting IntervalN
        """

        if isinstance(pitch_a, str):
            pitch_a = DiatonicPitch.parse(pitch_a)
        if isinstance(pitch_b, str):
            pitch_b = DiatonicPitch.parse(pitch_b)

        if pitch_a is None or pitch_b is None:
            raise Exception('None passed as pitch argument.')
        
        pitch_chromatic_distance = pitch_b.chromatic_distance - pitch_a.chromatic_distance         
        
        # This is just a subtraction of (a_index, a_octave) - (b_index, b_octave)
        # this is origin 0
        tone_index_diff = pitch_b.diatonic_tone.diatonic_index - pitch_a.diatonic_tone.diatonic_index
        octave_diff = pitch_b.octave - pitch_a.octave
            
        # tone_index_diff is the diatonic distance between a and b
        tone_index_diff += octave_diff * 7    # origin 0
        octave = IntervalN._compute_octave(tone_index_diff) 
        
        # compute the interval type.  Reduce values to within those of INTERVAL_MAP
        d_d = tone_index_diff - 7 * octave
        c_d = pitch_chromatic_distance - 12 * octave  
        # (0, -1) is special, and we need to call it out as a special case.
        (dd, cd) = ((abs(d_d)), -1 if c_d == -1 and d_d == 0 else abs(c_d))
        if (dd, cd) not in IntervalN.INTERVAL_MAP:
            raise Exception('\'{0}\' and \'{1}\' do not form a valid interval.'.format(pitch_a, pitch_b))
        interval_type = IntervalN.INTERVAL_MAP[(dd, cd)]
        
        # as usual, the diatonic distance is origin 1, so bump it in the correct sign.
        return IntervalN((abs(tone_index_diff) + 1) * IntervalN._sign(tone_index_diff), interval_type)        
    
    @property
    def interval_type(self):
        return self.__interval_type
    
    @property
    def diatonic_distance(self):
        return self.__diatonic_distance
    
    @property
    def chromatic_distance(self):
        return self.__chromatic_distance
    
    def is_same(self, other_interval):
        """
        Determine if this interval is the same as another.
        
        Args:
          other_interval: (IntervalN) that we compare to
        Returns: True?False
        """
        if other_interval is None:
            return False
        if not isinstance(other_interval, self.__class__):
            raise Exception('Cannot compare interval with {0}'.format(type(other_interval)))
        return self.interval_type == other_interval.interval_type and \
            self.diatonic_distance == other_interval.diatonic_distance
    
    def get_end_tone(self, diatonic_tone):
        """
        Given a tone and this interval, assume the tone is the lower tone of the interval.
        Compute the upper tone.
        
        Args:
          diatonic_tone: DiatonicTone
          
        Returns:
          DiatonicTone of upper tone
        """
        
        result = self.get_end_pitch(DiatonicPitch(4, diatonic_tone.diatonic_symbol))
        return result.diatonic_tone if result else None      
        
    def get_end_pitch(self, pitch):
        """
        Given a pitch and this interval, Assuming pitch is the starting pitch of the interval,
        compute the end pitch.
        
        Args:
          pitch: DiatonicPitch
          
        Returns:
          DiatonicPitch of end tone
        """
        diatonic_dist = pitch.diatonic_distance() + self.diatonic_distance
        tone_index = diatonic_dist % 7
        end_pitch_string = DiatonicTone.get_diatonic_letter(tone_index) 
        end_pitch_octave = diatonic_dist // 7
        
        chromatic_dist = pitch.chromatic_distance + self.chromatic_distance
        
        normal_pitch = DiatonicPitch(end_pitch_octave, DiatonicFoundation.get_tone(end_pitch_string))
        
        alteration = chromatic_dist - normal_pitch.chromatic_distance
        
        end_pitch_string += DiatonicTone.augmentation(alteration)
        
        return DiatonicPitch.parse(end_pitch_string + ':' + str(end_pitch_octave)) 
    
    def get_start_tone(self, diatonic_tone):
        """
        Given a tone and this interval, assume the pitch is the upper tone of the interval.
        Compute the lower tone.
        
        Args:
          diatonic_tone: DiatonicTone
          
        Returns:
          DiatonicTone of the lower tone
        """
        result = self.get_start_pitch(DiatonicPitch(4, diatonic_tone.diatonic_symbol))
        return result.diatonic_tone if result else None 
     
    def get_start_pitch(self, pitch):
        """
        Given a pitch and this interval, assume the pitch is the upper tone of the interval.
        Compute the lower pitch.
        
        Args:
          pitch: DiatonicPitch
          
        Returns:
          DiatonicPitch of the lower tone
        """
        return (self.negation()).get_end_pitch(pitch)
    
    def semitones(self):
        """
        Compute the number of semitones encompassed by this interval;
        Algorithm: translate into interval [C-X] based on diatonic distance, then calculate semitones
                   based on that interval and augmentation offset.
        
        Args:
        Returns: number of semitones.
        """
        
        return abs(self.chromatic_distance)
    
    def __eq__(self, other):        
        return self.is_same(other)
    
    def __ne__(self, other):
        return not self.is_same(other)
    
    def __hash__(self):
        return hash(str(self))
    
    def __add__(self, interval):
        return IntervalN.add_intervals(self, interval)

    def __sub__(self, interval):
        return IntervalN.add_intervals(self, interval.negation())

    def __iadd__(self, interval):
        """
        Override s += y
        
        Args:
          interval: 
        """
        return self + interval

    def __isub__(self, interval):
        """
        Override s += y

        Args:
          interval:
        """
        return self - interval
    
    def negation(self):
        if self.diatonic_distance == 0:
            interval_type = IntervalType.Perfect if self.interval_type == IntervalType.Perfect else \
                IntervalType.Augmented if self.interval_type == IntervalType.Diminished else \
                IntervalType.Diminished
        else:
            interval_type = self.interval_type
        d = (abs(self.diatonic_distance) + 1) * (-1 if self.diatonic_distance > 0 else 1)
        return IntervalN(d, interval_type)
        
    def inversion(self):
        reduced = self.reduction()
        sgn = -1 if self.is_negative() else 1
        (d, c) = (sgn * 7 - reduced.diatonic_distance, sgn * 12 - reduced.chromatic_distance)
        (r, s) = IntervalN._abs(d, c)
        if not (r, s) in IntervalN.INTERVAL_MAP:              
            raise Exception('No valid inversion for {0}.'.format(self))        
        return IntervalN((abs(d) + 1) * (1 if d >= 0 else -1), IntervalN.INTERVAL_MAP[r, s])
    
    def reduction(self):
        octave = IntervalN._compute_octave(self.diatonic_distance)  
        (d, c) = (self.diatonic_distance - 7 * octave, self.chromatic_distance - 12 * octave)
        (r, s) = IntervalN._abs(d, c)
        if not (r, s) in IntervalN.INTERVAL_MAP:              
            raise Exception('No valid reduction for {0}.'.format(self))        
        return IntervalN((abs(d) + 1) * IntervalN._sign(d), IntervalN.INTERVAL_MAP[r, s])   
    
    @staticmethod
    def available_types(diatonic_distance):
        """
        Per diatonic distance, return the interval types that interval can have,
        
        Args:
          diatonic_distance: (int) 
        Returns:
          An array of IntervalType values.
        """
        if not isinstance(diatonic_distance, int) or diatonic_distance <= 0:
            return []
        return IntervalN.INTERVAL_AVAILABLE_TYPES[(diatonic_distance - 1) % 7 + 1]

    def is_negative(self):
        return IntervalN._sign(self.diatonic_distance) == -1
    
    def __str__(self):
        return '{0}{1}:{2}'.format('-' if IntervalN._sign(self.diatonic_distance) == -1 else '',
                                   IntervalType.short_notation(self.interval_type),
                                   abs(self.diatonic_distance) + 1)

    # Regex used for parsing IntervalN specification.
    INTERVAL_TYPE = '(P|m|M|A|d)'
    INTERVAL_TYPE_NAME = 'IntervalType'
    INTERVAL_TYPE_TAG = '?P<' + INTERVAL_TYPE_NAME + '>'
    INTERVAL_TYPE_PART = '(' + INTERVAL_TYPE_TAG + INTERVAL_TYPE + ')'
    
    DISTANCE = '[1-9]([0-9]*)'
    DISTANCE_NAME = 'Distance'
    GROUP_DISTANCE_TAG = '?P<' + DISTANCE_NAME + '>'
    DISTANCE_PART = '(' + GROUP_DISTANCE_TAG + DISTANCE + ')'
    
    INTERVAL_SIGN = '(\\+|\\-)'
    INTERVAL_SIGN_NAME = 'IntervalSign'
    INTERVAL_SIGN_TAG = '?P<' + INTERVAL_SIGN_NAME + '>'
    INTERVAL_SIGN_PART = '(' + INTERVAL_SIGN_TAG + INTERVAL_SIGN + ')'
    
    INTERVAL_PATTERN_STRING = INTERVAL_SIGN_PART + '?' + INTERVAL_TYPE_PART + ':' + DISTANCE_PART
    INTERVAL_PATTERN = re.compile(INTERVAL_PATTERN_STRING)
    
    INTERVAL_LTR_MAP = {'P': IntervalType.Perfect,
                        'A': IntervalType.Augmented,
                        'd': IntervalType.Diminished,
                        'M': IntervalType.Major,
                        'm': IntervalType.Minor}
    
    @staticmethod
    def parse(interval_string):
        """
        Parse a string into an interval.  The string has the format (sign)X:Y
        where X is in {d, m, M, P, A} and Y is an integer.  sign is '-' for negative intervals.
        """
        if not interval_string:
            raise Exception('Unable to parse interval string to completion: {0}'.format(interval_string))
        m = IntervalN.INTERVAL_PATTERN.match(interval_string)
        if not m:
            raise Exception('Unable to parse interval string to completion: {0}'.format(interval_string))   
        
        interval_type = IntervalN.INTERVAL_LTR_MAP[m.group(IntervalN.INTERVAL_TYPE_NAME)] 
        interval_distance = int(m.group(IntervalN.DISTANCE_NAME))
        
        sign_ltr = m.group(IntervalN.INTERVAL_SIGN_NAME)
        sign = 1 if sign_ltr is None else (1 if sign_ltr == '+' else -1)
        
        raw_distance = (interval_distance - 1) % 7 + 1
        if interval_type == IntervalType.Perfect:
            if raw_distance != 1 and raw_distance != 4 and raw_distance != 5:
                raise Exception('Illegal interval distance for perfect interval {0}'.format(interval_string))
        if interval_type == IntervalType.Major or interval_type == IntervalType.Minor:
            if raw_distance != 2 and raw_distance != 3 and raw_distance != 6 and raw_distance != 7:
                raise Exception('Illegal interval distance for major/minor interval {0}'.format(interval_string))
            
        # When sign is -1 and interval_distance = 0, we need to reflection_tests the interval
        if sign == -1 and interval_distance == 1:
            interval_type = IntervalType.Augmented if interval_type == IntervalType.Diminished else \
                            IntervalType.Diminished if interval_type == IntervalType.Augmented else IntervalType.Perfect
            
        return IntervalN(sign * interval_distance, interval_type)
    
    @staticmethod
    def add_intervals(a, b):
        """
        Static method to add two intervals.
        
        Args:
          a: first IntervalN
          b: second IntervalN
        Returns:
          combined interval
        Exception: When the combination is impossible, e.g. Dim 2nd + Min 6th
        """
        diatonic_count = a.diatonic_distance + b.diatonic_distance
        chromatic_count = a.chromatic_distance + b.chromatic_distance
        
        b_dc = diatonic_count % 7
        octaves = diatonic_count // 7
        b_ct = chromatic_count - 12 * octaves        
        
        if (b_dc, b_ct) not in IntervalN.INTERVAL_MAP:
            raise IntervalException('Illegal Addition {0} + {1}    ({2}, {3})'.format(a, b, diatonic_count + 1,
                                                                                      chromatic_count))
        return IntervalN(diatonic_count + 1, IntervalN.INTERVAL_MAP[(b_dc, b_ct)])
    
    @staticmethod
    def _compute_octave(d):
        return 0 if d == 0 else ((abs(d) - 1) // 7) * IntervalN._sign(d)
    
    @staticmethod
    def _abs(d, c):
        return (d, c) if d >= 0 else (-d, -c)
    
    @staticmethod
    def _sign(x):
        return 1 if x >= 0 else -1

    # The following methods compensate, in some limited cases, for not allowing doubly-augmented/diminished chords.

    @staticmethod
    def calculate_pure_distance(tone1, tone2):
        """
        Calculate the diatonic and chromatic distances between two tones, tone1 to tone2 (as if upwards)
        :param tone1:
        :param tone2:
        :return:
        """
        pitch1 = DiatonicPitch(4, tone1)
        pitch2 = DiatonicPitch(5 if DiatonicPitch.crosses_c(tone1, tone2, True) else 4, tone2)
        cc = pitch2.chromatic_distance - pitch1.chromatic_distance
        dd = (tone2.diatonic_index - tone1.diatonic_index) % 7
        return dd, cc

    @staticmethod
    def calculate_tone_interval(tone1, tone2):
        """
        Calculate interval between tone1 to tone2 assuming closest octave.
        :param tone1:
        :param tone2:
        :return:
        """
        dd, cc = IntervalN.calculate_pure_distance(tone1, tone2)
        if (dd, cc) not in IntervalN.INTERVAL_MAP:
            return None
        return IntervalN(dd + 1, IntervalN.INTERVAL_MAP[(dd, cc)])

    @staticmethod
    def end_tone_from_pure_distance(tone, dd, cc, up_down=True):
        """
        Given a tone and diatonic/chromatic distances compute the end tone above or below it.
        :param tone:
        :param dd:
        :param cc:
        :param up_down:
        :return:
        """
        new_dd = (tone.diatonic_index + dd) % 7 if up_down else (tone.diatonic_index - dd) % 7
        end_tone = DiatonicToneCache.get_tone(DiatonicTone.get_diatonic_letter(new_dd))
        aug = (cc - (end_tone.placement - tone.placement) % 12) if up_down else \
            (cc - (tone.placement - end_tone.placement) % 12)

        return DiatonicTone.alter_tone_by_augmentation(end_tone, aug)

    @staticmethod
    def _compute_octave1(d):
        return ((abs(d) - 1) // 7) * IntervalN._sign(d)

    @staticmethod
    def _print_interval_table():
        i_txt = ["P:1", "M:2", "m:3", "M:3", "d:4", "P:4", "P:5", "M:6", "M:7"]
        ivls = list()
        for i in range(0, len(i_txt)):
            ivls.append(IntervalN.parse(i_txt[i]))
        for i in range(0, len(ivls)):
            s = "[{0}] ".format(i)
            for j in range(0, len(ivls)):
                try:
                    summ = ivls[i] + ivls[j]
                except IntervalException:
                    summ = "X"
                s = s + str(summ) + "  "
            print(s)

# ==============================================================================
# ============================================================================== 7
# ==============================================================================

class ModalityType(object):

    # System wide known modality types.
    Major = None
    NaturalMinor = None
    MelodicMinor = None
    HarmonicMinor = None
    HarmonicMajor = None
    Ionian = None
    Dorian = None
    Phrygian = None
    Lydian = None
    Mixolydian = None
    Aeolian = None
    Locrian = None
    WholeTone = None
    MajorPentatonic = None
    EgyptianPentatonic = None
    MinorBluesPentatonic = None
    MajorBluesPentatonic = None
    MinorPentatonic = None
    HWOctatonic = None
    WHOctatonic = None
    MajorBlues = None
    MinorBlues = None

    def __init__(self, name):
        self.__name = name

    @property
    def name(self):
        return self.__name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if other is None or not isinstance(other, ModalityType):
            raise Exception('Must compare to non-None ModalityType.')
        return self.name == other.name

    def __hash__(self):
        return self.name.__hash__()


# Initialize System-wide modality types.
ModalityType.Major = ModalityType('Major')
ModalityType.NaturalMinor = ModalityType('NaturalMinor')
ModalityType.MelodicMinor = ModalityType('MelodicMinor')
ModalityType.HarmonicMinor = ModalityType('HarmonicMinor')
ModalityType.HarmonicMajor = ModalityType('HarmonicMajor')
ModalityType.Ionian = ModalityType('Ionian')
ModalityType.Dorian = ModalityType('Dorian')
ModalityType.Phrygian = ModalityType('Phrygian')
ModalityType.Lydian = ModalityType('Lydian')
ModalityType.Mixolydian = ModalityType('Mixolydian')
ModalityType.Aeolian = ModalityType('Aeolian')
ModalityType.Locrian = ModalityType('Locrian')
ModalityType.WholeTone = ModalityType('WholeTone')
ModalityType.MajorPentatonic = ModalityType('MajorPentatonic')
ModalityType.EgyptianPentatonic = ModalityType('EgyptianPentatonic')
ModalityType.MinorBluesPentatonic = ModalityType('MinorBluesPentatonic')
ModalityType.MajorBluesPentatonic = ModalityType('MajorBluesPentatonic')
ModalityType.MinorPentatonic = ModalityType('MinorPentatonic')
ModalityType.HWOctatonic = ModalityType('HWOctatonic')
ModalityType.WHOctatonic = ModalityType('WHOctatonic')
ModalityType.MajorBlues = ModalityType('MajorBlues')
ModalityType.MinorBlues = ModalityType('MinorBlues')

SYSTEM_MODALITIES = [
    ModalityType.Major,
    ModalityType.NaturalMinor,
    ModalityType.MelodicMinor,
    ModalityType.HarmonicMinor,
    ModalityType.HarmonicMajor,
    ModalityType.Ionian,
    ModalityType.Dorian,
    ModalityType.Phrygian,
    ModalityType.Lydian,
    ModalityType.Mixolydian,
    ModalityType.Aeolian,
    ModalityType.Locrian,
    ModalityType.WholeTone,
    ModalityType.MajorPentatonic,
    ModalityType.EgyptianPentatonic,
    ModalityType.MinorBluesPentatonic,
    ModalityType.MajorBluesPentatonic,
    ModalityType.MinorPentatonic,
    ModalityType.HWOctatonic,
    ModalityType.WHOctatonic,
    ModalityType.MajorBlues,
    ModalityType.MinorBlues,
]

# ==============================================================================
class ModalitySpec(object):
    """
    Class defining a modality specification that is used to initialize the Modality class.
    """
    
    def __init__(self, modality_type, incremental_interval_strs):
        """
        Constructor.

        :param modality_type:
        :param incremental_interval_strs:
        """
        if isinstance(modality_type, int):
            self.__modality_type = ModalityType(modality_type)    
        elif not isinstance(modality_type, ModalityType):
            raise Exception('Illegal modality type argument {0}.'.format(type(modality_type))) 
        else:
            self.__modality_type = modality_type
            
        if not isinstance(incremental_interval_strs, list):
            raise Exception('Illegal incremental intervals argument type {0}', type(incremental_interval_strs))
        
        self.__incremental_intervals = [IntervalN.parse(interval) for interval in incremental_interval_strs]
        
    @property
    def modality_type(self):
        return self.__modality_type
    
    @property
    def modality_name(self):
        return str(self.modality_type)
    
    @property
    def incremental_intervals(self):
        return self.__incremental_intervals   
    
    def __str__(self):
        return '{0}[{1}]'.format(self.modality_type, ', '.join(str(interval)
                                                               for interval in self.incremental_intervals))

# ==============================================================================
class Modality(object):
    """
    Defines a generic sense of modality, based on a collection of semitone offsets on a chromatic partition.
    """
    
    # This is a global accessible list of all possible starting diatonic tones.  This is useful for any modalities
    # that could have an empty (C-based) key signature, or otherwise that depends on each note being qualified
    # by it respectful augmentation.
    COMMON_ROOTS = ['C', 'D', 'E', 'F', 'G', 'A', 'B',
                    'Cb', 'Db', 'Eb', 'Fb', 'Gb', 'Ab', 'Bb',
                    'C#', 'D#', 'E#', 'F#', 'G#', 'A#', 'B#']
    
    DIATONIC_TONE_LETTERS = list('CDEFGAB')
    
    def __init__(self, modality_spec, modal_index=0):
        self.__modality_spec = modality_spec

        if modal_index < 0 or modal_index > len(self.modality_spec.incremental_intervals) - 2:
            raise Exception('modal_index \'{0}\' invalid, must be positive and less than \'{1}\'.'.
                            format(modal_index, len(self.modality_spec.incremental_intervals) - 1))
        self.__modal_index = modal_index
            
        self.__root_intervals = list()
        self.__incremental_intervals = list()
        sumit = self.__modality_spec.incremental_intervals[0]   # Should be P:1
        self.__root_intervals.append(sumit)
        self.__incremental_intervals.append(sumit)
        for i in range(modal_index + 1, len(self.modality_spec.incremental_intervals) + modal_index + 1):
            ri = i % len(self.modality_spec.incremental_intervals)
            if ri != 0:
                sumit = sumit + self.modality_spec.incremental_intervals[ri]
                self.__incremental_intervals.append(self.modality_spec.incremental_intervals[ri])
                self.__root_intervals.append(sumit)
        
        last_interval = self.__root_intervals[len(self.__root_intervals) - 1]    
        if str(last_interval) != 'P:8':
            raise Exception('Last interval {0} is not \'P:8\''.format(str(last_interval)))
    
    @property
    def modality_spec(self):
        return self.__modality_spec

    @property
    def modal_index(self):
        return self.__modal_index
    
    @property    
    def get_modality_name(self):
        return self.modality_spec.modality_name
    
    @property 
    def modality_type(self):
        return self.__modality_spec.modality_type
    
    @property
    def incremental_intervals(self):
        return self.__incremental_intervals
    
    @property
    def root_intervals(self):
        return self.__root_intervals
      
    def get_number_of_tones(self):
        return len(self.root_intervals) - 1

    @staticmethod
    def get_valid_root_tones():
        return Modality.COMMON_ROOTS

    def get_tonal_scale(self, diatonic_tone):
        """
        Given a tone root, compute the tonal scale for this modality.
        Treat this as a protected static method.

        Args:
          diatonic_tone: DiatonicTone for the root.
        Returns:
          List of DiatonicTone's in scale order for the input tone. The starting and end tone are the same.
        """
        tones = []

        for interval in self.root_intervals:
            tones.append(interval.get_end_tone(diatonic_tone))

        return tones
    
    def __str__(self):
        return '{0}{1}'.format(str(self.modality_spec),
                               '[{0}]'.format(self.modal_index) if self.modal_index != 0 else '')

    @staticmethod
    def find_modality(tones):
    #    from tonalmodel.diatonic_modality import DiatonicModality
        answers = list()
        answers.extend(DiatonicModality.find_modality(tones))

    #    from tonalmodel.pentatonic_modality import PentatonicModality
        answers.extend(PentatonicModality.find_modality(tones))
        return answers
    
# ==============================================================================\
class DiatonicModality(Modality):
    """
    This class represents diatonic modalities - scales with 7 tones over the 12 tone chromatic scale.
    These include Major, Minor, and Modal scales.
    """
    DIATONIC_MODALITIES = [
                           ModalityType.Major,
                           ModalityType.NaturalMinor,
                           ModalityType.MelodicMinor,
                           ModalityType.HarmonicMinor,
                           ModalityType.HarmonicMajor,
                           ModalityType.Ionian,
                           ModalityType.Dorian,
                           ModalityType.Phrygian,
                           ModalityType.Lydian,
                           ModalityType.Mixolydian,
                           ModalityType.Aeolian,
                           ModalityType.Locrian,
                           ]
    
    MODALITY_DEFINITION_MAP = {
        ModalityType.Major: ModalitySpec(ModalityType.Major, ['P:1', 'M:2', 'M:2', 'm:2', 'M:2', 'M:2', 'M:2', 'm:2']),
        ModalityType.NaturalMinor: ModalitySpec(ModalityType.NaturalMinor, ['P:1', 'M:2', 'm:2', 'M:2', 'M:2', 'm:2',
                                                                            'M:2', 'M:2']),
        ModalityType.MelodicMinor: ModalitySpec(ModalityType.MelodicMinor, ['P:1', 'M:2', 'm:2', 'M:2', 'M:2', 'M:2',
                                                                            'M:2', 'm:2']),
        ModalityType.HarmonicMinor: ModalitySpec(ModalityType.HarmonicMinor, ['P:1', 'M:2', 'm:2', 'M:2', 'M:2', 'm:2',
                                                                              'A:2', 'm:2']),
        ModalityType.HarmonicMajor: ModalitySpec(ModalityType.HarmonicMajor, ['P:1', 'M:2', 'M:2', 'm:2', 'M:2', 'm:2',
                                                                              'A:2', 'm:2']),
        ModalityType.Ionian: ModalitySpec(ModalityType.Ionian, ['P:1', 'M:2', 'M:2', 'm:2', 'M:2', 'M:2', 'M:2',
                                                                'm:2']),
        ModalityType.Dorian: ModalitySpec(ModalityType.Dorian, ['P:1', 'M:2', 'm:2', 'M:2', 'M:2', 'M:2', 'm:2',
                                                                'M:2']),
        ModalityType.Phrygian: ModalitySpec(ModalityType.Phrygian, ['P:1', 'm:2', 'M:2', 'M:2', 'M:2', 'm:2', 'M:2',
                                                                    'M:2']),
        ModalityType.Lydian: ModalitySpec(ModalityType.Lydian, ['P:1', 'M:2', 'M:2', 'M:2', 'm:2', 'M:2', 'M:2',
                                                                'm:2']),
        ModalityType.Mixolydian: ModalitySpec(ModalityType.Mixolydian, ['P:1', 'M:2', 'M:2', 'm:2', 'M:2', 'M:2',
                                                                        'm:2', 'M:2']),
        ModalityType.Aeolian: ModalitySpec(ModalityType.Aeolian, ['P:1', 'M:2', 'm:2', 'M:2', 'M:2', 'm:2', 'M:2',
                                                                  'M:2']),
        ModalityType.Locrian: ModalitySpec(ModalityType.Locrian, ['P:1', 'm:2', 'M:2', 'M:2', 'm:2', 'M:2', 'M:2',
                                                                  'M:2']),
    }

    @staticmethod
    def create(modality_type, modal_index=0):
        if modality_type not in DiatonicModality.DIATONIC_MODALITIES:
            raise Exception('Type parameter is not diatonic.')
        if modality_type not in DiatonicModality.MODALITY_DEFINITION_MAP:
            raise Exception('Illegal diatonic modality value: {0} - Check Modality_definition_map'.format(
                str(modality_type)))
        return Modality(DiatonicModality.MODALITY_DEFINITION_MAP[modality_type], modal_index)

    @staticmethod
    def diatonic_modality_types_as_string_array():
        answer = [t.name for t in DiatonicModality.DIATONIC_MODALITIES]
        return answer

    @staticmethod
    def find_modality(tones):
        answers = list()
        if len(tones) == 7:
            for t in [ModalityType.Major, ModalityType.NaturalMinor, ModalityType.MelodicMinor,
                      ModalityType.HarmonicMinor, ModalityType.HarmonicMajor]:
                modality_spec = DiatonicModality.MODALITY_DEFINITION_MAP[t]

                p1 = IntervalN.parse('P:1')
                for scale_start in range(0, 7):
                    intervals = [p1] + [IntervalN.calculate_tone_interval(tones[(scale_start + i) % 7],
                                                                         tones[(scale_start + i + 1) % 7])
                                        for i in range(0, len(tones))]
                    if intervals == modality_spec.incremental_intervals:
                        answers.append(DiatonicModality.create(t, (-scale_start) % len(tones)))
        return answers
    
# ==============================================================================
class BluesModality(Modality):
    """
    This class represents major and minor blues modalities - scales with 6 tones over the 12 tone chromatic partition.
    """
    BLUES_MODALITIES = [
                        ModalityType.MajorBlues,
                        ModalityType.MinorBlues,
                        ]
    MODALITY_DEFINITION_MAP = {
        ModalityType.MajorBlues: ModalitySpec(ModalityType.MajorBlues, ['P:1', 'M:2', 'A:1', 'm:2', 'm:3',
                                                                        'M:2', 'm:3']),   # Ascending
        ModalityType.MinorBlues: ModalitySpec(ModalityType.MinorBlues, ['P:1', 'm:3', 'M:2', 'A:1', 'm:2',
                                                                        'm:3', 'M:2']),   # Ascending
        }

    @staticmethod
    def create(modality_type, modal_index=0):
        if modality_type not in BluesModality.BLUES_MODALITIES:
            raise Exception('Type parameter is not blues.')
        if modality_type not in BluesModality.MODALITY_DEFINITION_MAP:
            raise Exception('Illegal diatonic modality value: {0} - Check Modality_definition_map'.format(
                str(modality_type)))
        return Modality(BluesModality.MODALITY_DEFINITION_MAP[modality_type], modal_index)

    @staticmethod
    def blues_modality_types_as_string_array():
        answer = [str(t) for t in BluesModality.BLUES_MODALITIES]
        return answer

# ==============================================================================
class WholeToneModality(Modality):
    """
    This class represents whole tone modalities - scales with 6 tones over the 12 tone chromatic scale.
    All tones are 2 semitones apart.
    """

    WHOLE_TONE_SPEC = ModalitySpec(ModalityType.WholeTone, ['P:1', 'M:2', 'M:2', 'M:2',
                                                            'M:2', 'M:2', 'd:3'])

    @staticmethod
    def create(modality_type, modal_index=0):
        if modality_type != ModalityType.WholeTone:
            raise Exception('Type parameter is not WholeTone.')
        return Modality(WholeToneModality.WHOLE_TONE_SPEC, modal_index)
    
# ==============================================================================
class PentatonicModality(Modality):
    """
    This class represents 5 pentatonic modalities - scales with 5 tones over the 12 tone chromatic partition.
    With circular succession, each is a rotation of the prior.
    """
    PENTATONIC_MODALITIES = [
                           ModalityType.MajorPentatonic, 
                           ModalityType.EgyptianPentatonic,
                           ModalityType.MinorBluesPentatonic,
                           ModalityType.MajorBluesPentatonic,
                           ModalityType.MinorPentatonic,
                           ]
    
    MODALITY_DEFINITION_MAP = {
        ModalityType.MajorPentatonic: ModalitySpec(ModalityType.MajorPentatonic, ['P:1', 'M:2', 'M:2', 'm:3', 'M:2',
                                                                                  'm:3']),
        ModalityType.EgyptianPentatonic: ModalitySpec(ModalityType.EgyptianPentatonic, ['P:1', 'M:2', 'm:3', 'M:2',
                                                                                        'm:3', 'M:2']),
        ModalityType.MinorBluesPentatonic: ModalitySpec(ModalityType.MinorBluesPentatonic, ['P:1', 'm:3', 'M:2', 'm:3',
                                                                                            'M:2', 'M:2']),
        ModalityType.MajorBluesPentatonic: ModalitySpec(ModalityType.MajorBluesPentatonic, ['P:1', 'M:2', 'm:3', 'M:2',
                                                                                            'M:2', 'm:3']),
        ModalityType.MinorPentatonic: ModalitySpec(ModalityType.MinorPentatonic, ['P:1', 'm:3', 'M:2', 'M:2', 'm:3',
                                                                                  'M:2']),
    }

    @staticmethod
    def create(modality_type, modal_index=0):
        if modality_type not in PentatonicModality.PENTATONIC_MODALITIES:
            raise Exception('Type parameter is not diatonic.')
        if modality_type not in PentatonicModality.MODALITY_DEFINITION_MAP:
            raise Exception('Illegal diatonic modality value: {0} - Check Modality_definition_map'.format(
                str(modality_type)))
        return Modality(PentatonicModality.MODALITY_DEFINITION_MAP[modality_type], modal_index)

    @staticmethod
    def pentatonic_modality_types_as_string_array():
        answer = [str(t) for t in PentatonicModality.PENTATONIC_MODALITIES]
        return answer

    @staticmethod
    def find_modality(tones):
        answers = list()
        if len(tones) == 5:
            for t in [ModalityType.MajorPentatonic]:
                modality_spec = PentatonicModality.MODALITY_DEFINITION_MAP[t]

                p1 = IntervalN.parse('P:1')
                for scale_start in range(0, 5):
                    intervals = [p1] + [IntervalN.calculate_tone_interval(tones[(scale_start + i) % 5],
                                                                         tones[(scale_start + i + 1) % 5])
                                        for i in range(0, len(tones))]
                    if intervals == modality_spec.incremental_intervals:
                        answers.append(PentatonicModality.create(t, (-scale_start) % len(tones)))
        return answers
    
# ==============================================================================
class OctatonicModality(Modality):
    """
    Defines the octatonic tonality.  The scale is uniform tone-alternating half and whole steps.
    """
    OCTATONIC_MODALITIES = [
                           ModalityType.HWOctatonic, 
                           ModalityType.WHOctatonic,
                           ]
    
    MODALITY_DEFINITION_MAP = {
        ModalityType.HWOctatonic: ModalitySpec(ModalityType.HWOctatonic, ['P:1', 'm:2', 'M:2', 'm:2', 'M:2', 'A:1',
                                                                          'M:2', 'm:2', 'M:2']),
        ModalityType.WHOctatonic: ModalitySpec(ModalityType.WHOctatonic, ['P:1', 'M:2', 'm:2', 'M:2', 'A:1', 'M:2',
                                                                          'm:2', 'M:2', 'm:2']),
        }

    @staticmethod
    def create(modality_type, modal_index = 0):
        if modality_type not in OctatonicModality.OCTATONIC_MODALITIES:
            raise Exception('Type parameter is not diatonic.')
        if modality_type not in OctatonicModality.MODALITY_DEFINITION_MAP:
            raise Exception('Illegal diatonic modality value: {0} - Check Modality_definition_map'.format(
                str(modality_type)))
        return Modality(OctatonicModality.MODALITY_DEFINITION_MAP[modality_type], modal_index)
    
    @staticmethod
    def octatonic_modality_types_as_string_array():
        answer = [str(t) for t in OctatonicModality.OCTATONIC_MODALITIES]
        return answer
    
# ==============================================================================
class ModalityFactory(object):
    """
    Static class of utility method for Modality creation, of the system-based modalities.
    """

    ModalityInitDict = dict()

    @staticmethod
    def register_modality(modality_type, modality_spec):
        if modality_type not in ModalityFactory.ModalityInitDict:
            ModalityFactory.ModalityInitDict[modality_type] = modality_spec

    @staticmethod
    def deregister_modality(modality_type):
        if modality_type in ModalityFactory.ModalityInitDict:
            del ModalityFactory.ModalityInitDict[modality_type]

    @staticmethod
    def is_registered(modality_type):
        return modality_type in ModalityFactory.ModalityInitDict
   
    @staticmethod
    def create_modality(modality_type, modal_index=0):
        """
        Create modality by modality type
        
        Args:
        modality_type: type of modality to create.
        
        Returns: The respective modality object.
        Raises: Exception if type is not recognized.
        
        Note: update this method with each new Modality
        """
        if modality_type in ModalityFactory.ModalityInitDict:
            return Modality(ModalityFactory.ModalityInitDict[modality_type], modal_index)

        raise Exception('Unrecognized modality type {0} in create_modality'.format(modality_type))


for key, value in DiatonicModality.MODALITY_DEFINITION_MAP.items():
    ModalityFactory.register_modality(key, value)


for key, value in BluesModality.MODALITY_DEFINITION_MAP.items():
    ModalityFactory.register_modality(key, value)


ModalityFactory.ModalityInitDict[WholeToneModality.WHOLE_TONE_SPEC.modality_type] = \
    WholeToneModality.WHOLE_TONE_SPEC


for key, value in PentatonicModality.MODALITY_DEFINITION_MAP.items():
    ModalityFactory.register_modality(key, value)


for key, value in OctatonicModality.MODALITY_DEFINITION_MAP.items():
    ModalityFactory.register_modality(key, value)

# ==============================================================================
class Tonality(object):
    """
    Tonality is a class that is based on a modality and a root diatonic tone.  So whereas modality might be 'Ionian', 
        tonality would be that, but rooted (first tone) at a given diatonic tone.
    """

    def __init__(self, modality, diatonic_tone):
        """
        Constructor.
        :param modality: Modality specified.
        :param diatonic_tone: DiatonicTone being used as root.

        diatonic_tone is the modal_index tone into some tonality based on the given modality.

        Note: (Using E Major, modal+index=1 as an example)
              self.basis_tone: is the tonality first tone, as if modal_index==0. (E)
              self.root_tone: is the tonality first tone with modal_index taken into account. (F#)
        """
        if isinstance(diatonic_tone, str):
            self.__diatonic_tone = DiatonicToneCache.get_tone(diatonic_tone)
        else:
            self.__diatonic_tone = diatonic_tone

        self.__modality_type = modality.modality_type
        self.__modality = modality
        self.__annotation = self.modality.get_tonal_scale(self.diatonic_tone)

        self.__basis_tone = (self.annotation[:-1])[-self.modal_index]

    @staticmethod
    def create(modality_type, diatonic_tone, modal_index=0):
        """
        Constructor.
        :param modality_type: ModalityType being used.
        :param diatonic_tone: DiatonicTone being used as root.
        :param modal_index: (origin 0), which of the tonality's tone is the actual root_tone.
        """
        if isinstance(diatonic_tone, str):
            base_diatonic_tone = DiatonicToneCache.get_tone(diatonic_tone)
        else:
            base_diatonic_tone = diatonic_tone
        return Tonality(ModalityFactory.create_modality(modality_type, modal_index), base_diatonic_tone)

    @staticmethod
    def create_on_basis_tone(basis_tone, modality_type, modal_index=0):
        diatonic_tone = DiatonicToneCache.get_tone(basis_tone) if isinstance(basis_tone, str) else basis_tone

        raw_modality = ModalityFactory.create_modality(modality_type, 0)
        scale = raw_modality.get_tonal_scale(diatonic_tone)
        return Tonality.create(modality_type, scale[modal_index], modal_index)

    @property
    def modality_type(self):
        return self.__modality_type
         
    @property 
    def modality(self):
        return self.__modality
  
    @property
    def diatonic_tone(self):
        return self.__diatonic_tone

    @property
    def root_tone(self):
        return self.__diatonic_tone

    @property
    def basis_tone(self):
        return self.__basis_tone

    @property
    def modal_index(self):
        return self.__modality.modal_index
  
    @property
    def annotation(self):
        return self.__annotation

    @property
    def cardinality(self):
        return self.modality.get_number_of_tones()
    
    def get_tone(self, index):
        if index < 0 or index >= len(self.annotation):
            return None
        return self.annotation[index]
    
    def __str__(self):
        root_info = ' {0}({1})'.format(self.root_tone.diatonic_symbol, self.modal_index) \
            if self.modal_index != 0 else ''
        return '{0}-{1}{2}'.format(self.basis_tone.diatonic_symbol, self.modality.modality_type, root_info)

    def get_tone_by_letter(self, letter):
        tones = []
        for tone in self.annotation:
            if tone.diatonic_letter == letter:
                tones.append(tone)
        return tones

    @staticmethod
    def find_tonality(tones):
        modalities = Modality.find_modality(tones)
        answers = list()
        for modality in modalities:
            answers.append(Tonality.create(modality.modality_type, tones[0], modality.modal_index))
        return answers
    
# ==============================================================================
class Range(object):
    """
    Range class encapsulates an inclusive range of (integer) values
    """

    def __init__(self, start_index, end_index):
        """
        Constructor.
        
        Args:
          start_index: beginning numeric (integer).
          end_index: last and included numeric (integer)
          
        Note: Throws exception if begin precedes start, not not integer input.
        """
        if not isinstance(start_index, int):
            raise Exception("Start value in range must be integer {0}".format(type < start_index))
        if not isinstance(end_index, int):
            raise Exception("End value in range must be integer {0}".format(type < end_index))
        if end_index < start_index:
            raise Exception('Illegal range {0} > {1}'.format(start_index, end_index))
        
        self.__start_index = start_index
        self.__end_index = end_index
        
    @property
    def start_index(self):
        return self.__start_index
    
    @property
    def end_index(self):
        return self.__end_index
    
    def __str__(self):
        return 'R[{0}, {1}]'.format(self.start_index, self.end_index)
    
    def size(self):
        """
        Return the number of integer values in range.
        """
        return self.end_index - self.start_index + 1
    
    def is_inbounds(self, index):
        """
        Determine if index is in bounds to this range.
        
        Args:
          index: numeric value
        Returns:
          boolean for inclusion.
        Note: unpredictable result for non-numeric
        return index >= self.start_index and index <= self.end_index
        """
        return self.end_index >= index >= self.start_index
    
# ==============================================================================
class PitchRange(Range):
    """
    PitchRange defines an inclusive chromatic pitch range.
    """

    def __init__(self, start_index, end_index):
        """
        Constructor
        
        Args:
          start_index: integer start chromatic pitch index
          end_index: integer end chromatic pitch index
        Exceptions: is start, end out of range of absolute chromatic range, plus those from Range.
        """
        Range.__init__(self, start_index, end_index)
        if start_index < ChromaticScale.chromatic_start_index():
            raise Exception(
                "Start index {0} lower than chromatic start {1}".format(start_index,
                                                                        ChromaticScale.chromatic_start_index()))
        if end_index > ChromaticScale.chromatic_end_index():
            raise Exception(
                "end index {0} higher than chromatic end {1}".format(end_index, ChromaticScale.chromatic_end_index()))
        
    @staticmethod
    def create(start_spn, end_spn):
        """
        Create PitchRange based on start and end scientific pitch notation.
        
        Args:
          start_spn: start spn (pitch string).
          end_spn: end spn (pitch string).
        Returns:
          PitchRange based on inputs.
        """
        start = DiatonicFoundation.get_chromatic_distance(DiatonicPitch.parse(start_spn)
                                                          if isinstance(start_spn, str) else start_spn)
        end = DiatonicFoundation.get_chromatic_distance(
            DiatonicPitch.parse(end_spn) if isinstance(end_spn, str) else end_spn)
        return PitchRange(start, end)
    
    def is_location_inbounds(self, location):
        """
        Determines if given chromatic location is in bounds of range.
        
        Args:
          location: chromatic location
        Returns:
          boolean indicating if in bounds.
        """
        return self.is_inbounds(ChromaticScale.location_to_index(location))
    
    def is_pitch_inbounds(self, pitch):
        """
        Determines if given chromatic location is in bounds of range.
        
        Args:
          pitch: spn text for pitch, e.g. 'c:4' or DiatonticPitch object.
        Returns:
          boolean indicating if in bounds.
        """
        p = DiatonicPitch.parse(pitch) if isinstance(pitch, str) else pitch
        return self.is_inbounds(DiatonicFoundation.get_chromatic_distance(p))
    
    def find_lowest_placement_in_range(self, placement):
        """
        For a given chromatic placement (0, ..., 11) find the lowest chromatic index 
        in the range for it.
        """
        if placement < 0 or placement >= 12:
            raise Exception('Illegal placement value {0} must be between 0 and 11'.format(placement))
        start_partition = ChromaticScale.index_to_location(self.start_index)[0]
        end_partition = ChromaticScale.index_to_location(self.end_index)[0]
        lowest_index = -1
        for partition in range(start_partition, end_partition + 1):
            if self.is_location_inbounds((partition, placement)):
                lowest_index = ChromaticScale.location_to_index((partition, placement))
                break
        return lowest_index
    
    def __str__(self):
        return 'P-R({0}, {1})'.format(DiatonicFoundation.map_to_diatonic_scale(self.start_index)[0],
                                      DiatonicFoundation.map_to_diatonic_scale(self.end_index)[0])
    
# ==============================================================================
class PitchScale(object):
    """
    Tonality based class to build a set of DiatonicPitch's from the tonality for a chromatic range.
    """

    def __init__(self, tonality, pitch_range):
        """
        Constructor.
        
        Args:
            tonality: the Tonality object for the scale.
            pitch_range: the PitchRange for the scale coverage.
        """
        self.__tonality = tonality
        self.__pitch_range = pitch_range
        
        self.__tone_scale = tonality.annotation
        self.__pitch_scale = self.__compute_pitch_scale()
        
    @property
    def tonality(self):
        return self.__tonality
    
    @property
    def pitch_range(self):
        return self.__pitch_range
    
    @property
    def tone_scale(self):
        return self.__tone_scale
    
    @property
    def pitch_scale(self):
        return self.__pitch_scale
        
    @staticmethod   
    def create_default(tonality):
        return PitchScale(tonality, PitchRange(ChromaticScale.chromatic_start_index(),
                                               ChromaticScale.chromatic_end_index()))

    @staticmethod
    def compute_tonal_pitches(tonality, pitch_range):
        """
        For a tonality and pitch range, compute all scale pitches in that range.

        :param tonality: Tonality
        :param pitch_range: PitchRange
        :return:
        """
        pitch_scale = PitchScale(tonality, pitch_range)
        return pitch_scale.pitch_scale
    
    def __compute_pitch_scale(self):
        (tone_index, pitch_index) = self.__find_lowest_tone()   # Determine the lowest tone in the range
        if tone_index == -1:
            return []
        scale = [DiatonicPitch(ChromaticScale.index_to_location(pitch_index)[0],
                               self.tone_scale[tone_index].diatonic_symbol)]
        
        # Given the first pitch, sync up with the incremental intervals on the tonality, and move forward, computing
        # each scale pitch until we are out of range.  
        # Note: be sure to skip the first incremental interval which should be P:1
        prior_pitch = scale[0]
        while True:
            tone_index += 1
            if tone_index > len(self.tone_scale) - 1:
                tone_index = 1  # skip 0 as that should be P:1
            incremental_interval = self.tonality.modality.incremental_intervals[tone_index]
            current_pitch = incremental_interval.get_end_pitch(prior_pitch)
            if current_pitch.chromatic_distance > self.pitch_range.end_index:
                break
            scale.append(current_pitch)
            prior_pitch = current_pitch
            
        return scale
        
    def __find_lowest_tone(self):
        tone_index = -1
        pitch_index = 300
        # loop over scale tones
        #    for each, find the lowest chromatic index in range (if any), and set that as the 'find' 
        for tone in self.tone_scale:
            #  Get the lowest chromatic index in range, for the given tone
            lowest_index = self.pitch_range.find_lowest_placement_in_range(tone.placement)
            if lowest_index != -1:
                if lowest_index < pitch_index:
                    tone_index = self.tone_scale.index(tone)
                    pitch_index = lowest_index
        return tone_index, pitch_index

    @staticmethod
    def compute_closest_scale_tones(tonality, pitch):
        """
        Returns either the pitch if in tonality, or lower/upper pitches in scale to pitch.
        :param tonality:
        :param pitch:
        :return: an array with 1 element if exact match, otherwise closest lower and upper bound pitches
                 in given tonality.
        """
    #    from tonalmodel.pitch_range import PitchRange
        chromatic_index = pitch.chromatic_distance
        pitch_range = PitchRange(max(chromatic_index - 12, ChromaticScale.chromatic_start_index()),
                                 min(chromatic_index + 12, ChromaticScale.chromatic_end_index()))
        pitch_scale = PitchScale(tonality, pitch_range)

        for i in range(0, len(pitch_scale.pitch_scale)):
            p = pitch_scale.pitch_scale[i]
            if p.chromatic_distance < chromatic_index:
                continue
            if p.chromatic_distance == chromatic_index:
                return [p]
            if i == 0:
                raise Exception(
                    'unexpected logic issue in compute_closest_pitch_range {0}, {1]'.format(tonality, pitch))
            return [pitch_scale.pitch_scale[i - 1], p]
        raise Exception(
            'unexpected logic fail in compute_closest_pitch_range {0}, {1]'.format(tonality, pitch))

    @staticmethod
    def compute_tonal_pitch_range(tonality, pitch, lower_index, upper_index):
        """
        Find all pitches within range of tonality based on an arbitrary pitch given as starting point.
        In all cases, look at the closest pitches (1 or 2) as origin 0, and the lower/upper as counting indices
        below or up from them.
        :param tonality:
        :param pitch:
        :param lower_index:
        :param upper_index:
        :return:
        """
        import math
    #    from tonalmodel.pitch_range import PitchRange
        starting_points = PitchScale.compute_closest_scale_tones(tonality, pitch)

        # Determine the number of octaves that will cover the given range.
        up_chrom = max(0, int(math.ceil(float(abs(upper_index)) / len(tonality.annotation)) * 12) *
                       (-1 if upper_index < 0 else 1))
        down_chrom = min(0, int(math.ceil(float(abs(lower_index)) / len(tonality.annotation)) * 12) *
                         (-1 if lower_index < 0 else 1))

        # Compute all pitches within that range
        low = max(starting_points[0].chromatic_distance + down_chrom, ChromaticScale.chromatic_start_index())
        high = min((starting_points[0].chromatic_distance if len(starting_points) == 1
                    else starting_points[1].chromatic_distance) + up_chrom, ChromaticScale.chromatic_end_index())

        pitch_range = PitchRange(low, high)
        pitch_scale = PitchScale(tonality, pitch_range).pitch_scale

        # The first starting point is either the enharmonic equivalent to pitch, or the lower scale pitch to the pitch.
        # lower_starting_index is the index in pitch_scale for that pitch.
        lower_starting_index = [index for index in range(0, len(pitch_scale))
                                if pitch_scale[index].chromatic_distance == starting_points[0].chromatic_distance][0]

        if len(starting_points) == 1:
            full_range = range(lower_starting_index + lower_index,
                               min(lower_starting_index + upper_index + 1, len(pitch_scale)))
            return [pitch_scale[i] for i in full_range]
        else:
            upper_starting_index = [index for index in range(0, len(pitch_scale))
                                    if pitch_scale[index].chromatic_distance ==
                                    starting_points[1].chromatic_distance][0]
            lo = lower_index + (lower_starting_index if lower_index <= 0 else upper_starting_index)
            hi = upper_index + (lower_starting_index if upper_index < 0 else upper_starting_index)
            full_range = range(lo, hi + 1)
            return [pitch_scale[i] for i in full_range]
        
# ==============================================================================
# ============================================================================== 8
# ==============================================================================

class Position(object):
    """
    Class to represent position in music time.  This is primarily an encapsulation of Fraction,
    however, the typing is used to ensure some level of usage safety.  Ref. the operator overloading.
    """

    def __init__(self, *args, **kwargs):
        # args -- tuple of anonymous arguments
        # kwargs -- dictionary of named arguments
        """
        Constructor
                
        Args (1 parameter only)
          [0] duration_fraction (Fraction)
          
        Args (2 parameters)
          [0] numerator (int)
          [1] denominator (int)
        """
    #    from timemodel.duration import Duration
        if len(args) == 1:
            if isinstance(args[0], int):
                position_fraction = Fraction(args[0], 1)
            elif isinstance(args[0], Position):
                position_fraction = args[0].position
            elif isinstance(args[0], Duration):
                position_fraction = args[0].duration
            elif not isinstance(args[0], Fraction):
                raise Exception('Cannot create Position with {0} as type {1}', args[0], type(args[0]))
            else:
                position_fraction = args[0]
        elif len(args) == 2:
            if not isinstance(args[0], int) or not isinstance(args[1], int):
                raise Exception('Cannot create Position with {0}, {1] wity types {2}, {3}', args[0], args[1],
                                type(args[0]), type(args[1]))
            position_fraction = Fraction(args[0], args[1])
        else:
            raise Exception('Cannot create Position with {0} arguments', len(args))
            
        self.__position = position_fraction
        
    @property
    def position(self):
        return self.__position
    
    def __cmp__(self, other):
        return -1 if self.position < other.position else 1 if self.position > other.position else 0
    
    def __lt__(self, other):
        if isinstance(other, Position):
            return self.position < other.position
        else:
            return self.position < other
       
    def __le__(self, other):
        if isinstance(other, Position):
            return self.position <= other.position
        else:
            return self.position <= other
        
    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, Position):
            return self.position == other.position
        elif isinstance(other, int) or isinstance(other, float) or isinstance(other, Fraction):
            return self.position == other
        else:
            return Exception('Cannot == compare Position to type {0}.'.format(type(other)))
        
    def __hash__(self):
        return hash(self.position)
    
    def __ne__(self, other):
        if other is None:
            return False
        if isinstance(other, Position):
            return self.position != other.position
        elif isinstance(other, int) or isinstance(other, float) or isinstance(other, Fraction):
            return self.position != other
        else:
            return Exception('Cannot != compare Position to type {0}.'.format(type(other)))
    
    def __gt__(self, other):
    #    from timemodel.offset import Offset
        if other is None:
            return False
        if isinstance(other, int) or isinstance(other, float) or isinstance(other, Fraction):
            return self.position > other
        if isinstance(other, Position):
            return self.position > other.position
        if isinstance(other, Offset):
            return self.position > other.offset

    def __ge__(self, other):
        if isinstance(other, Position):
            return self.position >= other.position
        else:
            return self.position >= other
    
    def __add__(self, other):
 #       from timemodel.duration import Duration
 #       from timemodel.offset import Offset
        if isinstance(other, Fraction) or isinstance(other, int):
            return Position(self.position + other)
        elif isinstance(other, float):
            return Position(self.position + Fraction(other))
        elif isinstance(other, Duration):
            return Position(self.position + other.duration)
        elif isinstance(other, Offset):
            return Position(self.position + other.offset)
        else:
            raise Exception('+ operator: cannot add {0} type {1} to position'.format(other, type(other)))
        
    def __radd__(self, other):
        return self + other
        
    def __iadd__(self, other):
        return self + other       
        
    def __sub__(self, other):
 #       from timemodel.duration import Duration
 #       from timemodel.offset import Offset
        if isinstance(other, Fraction) or isinstance(other, int):
            return Position(self.position - other)
        if isinstance(other, float):
            return Position(self.position - Fraction(other))
        elif isinstance(other, Position):
            return Duration(self.position - other.position)
        elif isinstance(other, Duration):
            return Position(self.position - other.duration)
        elif isinstance(other, Offset):
            return Position(self.position - other.offset)
        else:
            raise Exception('Cannot subtract type {0} from position', type(other))
        
    def __isub__(self, other):
        return self - other
    
    def __rsub__(self, other):
        return -self.__sub__(other)
        
    def __neg__(self):
        return Position(-self.position)
    
    def __mul__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int):
            return Position(self.position * other)
        elif isinstance(other, float):
            return Position(self.position * Fraction(other))
        else:
            raise Exception('+ operator: cannot add {0} type {1} to position'.format(other, type(other)))
        
    def __imul__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int):
            return Position(self.position * other)
        if isinstance(other, float):
            return Position(self.position * Fraction(other))
        else:
            raise Exception('Cannot subtract type {0} from position', type(other)) 
        
    def __rmul__(self, other):
        return self * other
        
    def __str__(self):
        return str(self.position)
    
# ==============================================================================
class Duration(object):
    """
    Class to represent duration in music time.  This is primarily an encapsulation of Fraction,
    however, the typing is used to ensure some level of usage safety.  Ref. the operator overloading.
    """

    HALF = Fraction(1, 2)

    def __init__(self, *args, **kwargs):
        # args -- tuple of anonymous arguments
        # kwargs -- dictionary of named arguments
        """
        Constructor
        
        Args (1 parameter only)
          [0] duration_fraction (Fraction)
          
        Args (2 parameters)
          [0] numerator (int)
          [1] denominator (int)
        """
        if len(args) == 1:
            if isinstance(args[0], Duration):
                duration_fraction = args[0].duration
            elif not isinstance(args[0], Fraction) and not isinstance(args[0], int):
                raise Exception('Single argument to Duration must be fraction or int, not {0}.'.format(type(args[0])))
            else:
                duration_fraction = args[0] if isinstance(args[0], Fraction) else Fraction(args[0])
        elif len(args) == 2:
            if not isinstance(args[0], int) or not isinstance(args[1], int):
                raise Exception('For 2 arguments, both must be integer.')
            duration_fraction = Fraction(args[0], args[1])
        else:
            raise Exception('Only 1 or two arguments expected.')
            
        self.__duration = duration_fraction
        
    @property
    def duration(self):
        return self.__duration 
    
    @staticmethod
    def apply_half_dots(duration, num_dots):
        """
         Get the duration of a given duration with a number of dots applied.
         
         Args:
           duration: the duration to apply halving dots to
           num_dots: positive int value for number of dots
        Returns:
           new duration with number of dots applied to input duration.
        """
        target = Fraction(duration.duration.numerator, duration.duration.denominator)
        half_target = Fraction(duration.duration.numerator, duration.duration.denominator)
    
        while num_dots > 0:
            half_target *= Duration.HALF
            target = target + half_target
            num_dots -= 1
              
        return Duration(target)
    
    def apply_dots(self, num_dots):
        """
        Get the duration for this duration with number of dots applied.
        
        Args:
           num_dots: positive int value for number of dots to apply to self duration value
        Returns:
           new duration with number of dots applied to input duration.
        """
        return Duration.apply_half_dots(self, num_dots)
    
    def __cmp__(self, other):
        return -1 if self.duration < other.duration else 1 if self.duration > other.duration else 0
    
    def __lt__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.duration < other
        return self.duration < other.duration
       
    def __le__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.duration <= other
        return self.duration <= other.duration
        
    def __eq__(self, other):
    #    from timemodel.offset import Offset
        if other is None:
            return False
        elif isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.duration == other
        elif isinstance(other, Duration):
            return self.duration == other.duration
        elif isinstance(other, Offset):
            return self.duration == other.offset
        else:
            Exception('Cannot == compare Duration to type {0}.'.format(type(other)))
    
    def __ne__(self, other):
    #    from timemodel.offset import Offset
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.duration != other
        elif isinstance(other, Duration):
            return self.duration != other.duration
        elif isinstance(other, Offset):
            return self.duration != other.offset
        else:
            Exception('Cannot != compare Duration to type {0}.'.format(type(other)))
    
    def __gt__(self, other):
        if other is None:
            return False
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.duration > other
        if not isinstance(other, Duration):
            return False
        return self.duration > other.duration

    def __ge__(self, other):
        if other is None:
            return False
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.duration >= other
        if not isinstance(other, Duration):
            return False
        return self.duration >= other.duration
        
    def __add__(self, other):
    #    from timemodel.offset import Offset
        if isinstance(other, Fraction):
            return Duration(self.duration + other)
        if isinstance(other, int):
            return Duration(self.duration + other)
        elif isinstance(other, float):
            return Duration(self.duration + Fraction(other))
        elif isinstance(other, Duration):
            return Duration(self.duration + other.duration)
        elif isinstance(other, Position):
            return other + self
        elif isinstance(other, Offset):
            return Duration(self.duration + other.offset)
        else:
            raise Exception(
                '= operator for duration {0} cannot be applied to {1} of type {2}'.format(self, other, type(other)))
        
    def __radd__(self, other):
        return self + other
        
    def __iadd__(self, other):
        # dur = dur + position not possible, it is pos = pos + duration
        if isinstance(other, Position):
            raise Exception('+= operator for duration {0} cannot be applied to position {1}'.format(self, other))
        return self + other
    
    def __sub__(self, other):
    #    from timemodel.offset import Offset
        if isinstance(other, Fraction) or isinstance(other, int):
            return Duration(self.duration - other)
        if isinstance(other, float):
            return Duration(self.duration - Fraction(other))
        elif isinstance(other, Duration):
            return Duration(self.duration - other.duration)
        elif isinstance(other, Position):
            return Position(self.duration - other.position)
        elif isinstance(other, Offset):
            return Duration(self.duration - other.offset)
        else:
            raise Exception('- operator for duration {0} cannot can not subtract type {1}'.format(self, type(other)))
        
    def __rsub__(self, other):
        return -self.__sub__(other)
    
    def __isub__(self, other):
        if isinstance(other, Position):
            raise Exception('-= operator for duration {0} cannot be applied to position {1}'.format(self, other))
        return self - other
    
    def __neg__(self):
        return Duration(-self.duration)
    
    def __mul__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int):
            return Duration(self.duration * other)
        elif isinstance(other, float):
            return Duration(self.duration * Fraction(other))
        else:
            raise Exception('* operator for duration {0} cannot be used on type {1}'.format(self, type(other)))
        
    def __rmul__(self, other):
        return self * other
    
    def __imul__(self, other):
        return self.__mul__(other)

    def __hash__(self):
        return hash(str(self))
    
    def __str__(self):
        return str(self.duration)
    
# ==============================================================================
class Offset(object):
    """
    classdocs
    """

    def __init__(self, *args, **kwargs):
        # args -- tuple of anonymous arguments
        # kwargs -- dictionary of named arguments
        """
        Constructor
        
        Args (1 parameter only)
          [0] offset_fraction (Fraction)
          
        Args (2 parameters)
          [0] numerator (int)
          [1] denominator (int)
        """
        if len(args) == 1:
            if not isinstance(args[0], Fraction) and not isinstance(args[0], int) and not isinstance(args[0], float):
                raise Exception(
                    'Single argument to Duration must be fraction or int or float, not {0}.'.format(type(args[0])))
            offset_fraction = args[0] if isinstance(args[0], Fraction) else Fraction(args[0])
        elif len(args) == 2:
            if not isinstance(args[0], int) or not isinstance(args[1], int):
                raise Exception('For 2 arguments, both must be integer.')
            offset_fraction = Fraction(args[0], args[1])
        else:
            raise Exception('Only 1 or two arguments expected.')
            
        self.__offset = offset_fraction
     
    @property
    def offset(self):
        return self.__offset
    
    def __cmp__(self, other):
        return -1 if self.offset < other.offset else 1 if self.offset > other.offset else 0
    
    def __lt__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.offset < other
        return self.offset < other.offset
       
    def __le__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.offset <= other
        return self.offset <= other.offset
        
    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.offset == other
        if not isinstance(other, Offset):
            return False
        return self.offset == other.offset
    
    def __ne__(self, other):
        if other is None:
            return False
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.offset != other
        if not isinstance(other, Offset):
            return False
        return self.offset != other.offset
    
    def __gt__(self, other):
        if other is None:
            return False
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.offset > other
        if not isinstance(other, Offset):
            return False
        return self.offset > other.offset

    def __ge__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int) or isinstance(other, float):
            return self.offset >= other
        return self.offset >= other.offset    
    
    def __add__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int):
            return Offset(self.offset + other)
        elif isinstance(other, float):
            return Offset(self.offset + Fraction(other))
        elif isinstance(other, Duration):
            return Duration(self.offset + other.duration)
        elif isinstance(other, Position):
            return other + self
        elif isinstance(other, Offset):
            return Offset(self.offset + other.offset)
        else:
            raise Exception(
                '= operator for offset {0} cannot be applied to {1} of type {2}'.format(self, other, type(other)))
        
    def __radd__(self, other):
        return self + other
        
    def __iadd__(self, other):
        # We opt to make Offset so neutral that offset+=position or duration just augments offset
        # This turns out to be very useful, this overrides __add__ for position and duration arguments
        if isinstance(other, Position):
            other = Offset(other.position)
        elif isinstance(other, Duration):
            other = Offset(other.duration)
        return self + other
    
    def __sub__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int):
            return Offset(self.offset - other)
        elif isinstance(other, float):
            return Offset(self.offset - Fraction(other))
        elif isinstance(other, Position):
            return Position(self.offset - other.position)
        elif isinstance(other, Duration):
            return Duration(self.offset - other.duration)
        elif isinstance(other, Offset):
            return Offset(self.offset - other.offset)
        else:
            raise Exception('- operator for offset {0} cannot can not subtract type {1}'.format(self, type(other)))
        
    def __rsub__(self, other):
        return -self.__sub__(other)
    
    def __isub__(self, other):
        # We opt to make Offset so neutral that offset-=position or duration just augments offset
        # This turns out to be very useful, this overrides __sub__ for position and duration arguments
        if isinstance(other, Position):
            other = Offset(other.position)
        elif isinstance(other, Duration):
            other = Offset(other.duration)
        return self - other
    
    def __neg__(self):
        return Offset(-self.offset)
    
    def __mul__(self, other):
        if isinstance(other, Fraction) or isinstance(other, int):
            return Offset(self.offset * other)
        elif isinstance(other, float):
            return Offset(self.offset * Fraction(other))
        else:
            raise Exception('* operator for offset {0} cannot be used on type {1}'.format(self, type(other)))
        
    def __rmul__(self, other):
        return self * other
    
    def __imul__(self, other):
        return self.__mul__(other)   
    
    def __str__(self):
        return str(self.offset)
    
# ==============================================================================
class BeatPosition(object):
    """
    Class that represents a measure/beat location.  
    """

    def __init__(self, measure_number, beat_number):
        """
        Args:
          measure_number:  An integer representing the measure ordinal
          beat_number: A Fraction representing the beat within the measure.
        """
        self.__measure_number = measure_number
        self.__beat_number = beat_number
        
    @property
    def measure_number(self):
        return self.__measure_number
    
    @property
    def beat_number(self):
        return self.__beat_number

    @property
    def beat(self):
        return int(self.beat_number)

    @property
    def beat_fraction(self):
        return self.beat_number - self.beat
    
    def __lt__(self, other):
        return (self.measure_number < other.measure_number) or \
               (self.measure_number == other.measure_number and self.beat_number < other.beat_number)
    
    def __eq__(self, other):
        if other is None:
            return False
        return self.measure_number == other.measure_number and self.beat_number == other.beat_number
       
    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)
           
    def __ne__(self, other):
        if other is None:
            return False
        return self.measure_number != other.measure_number or self.beat_number != other.beat_number
    
    def __gt__(self, other):
        if other is None:
            return False
        return not self.__le__(other)
    
    def __ge__(self, other):
        if other is None:
            return False
        return not self.__lt__(other)

    def __hash__(self):
        return hash(str(self))
    
    def __str__(self):
        return 'BP[{0}, {1}]'.format(self.measure_number, self.beat_number)
    
# ==============================================================================
# The following are global variables used by TempoType, as we could not define these
# inside TempoType.
class TempoTypeHelper:
    RANGE_MAP = None
    ALL_TYPES = None


class TempoType(Enum):
    """
    Enum class for the quality of tempo names.
    """
    Larghissimo = 1
    Grave = 2
    Lento = 3
    Largo = 4
    Larghetto = 5
    Adagio = 6
    Adagietto = 7
    Andantino = 8
    Andante = 9
    AndanteModerato = 10
    MarciaModerato = 11
    Moderato = 12
    AllegroModerato = 13
    Allegretto = 14
    Allegro = 15
    Vivace = 16
    Vivacissimo = 17
    Allegrissimo = 18
    Presto = 19
    Prestissimo = 20

    def __str__(self):
        return self.name

    @staticmethod
    def class_init():
        """
        This method is a class initializer.  It is called outside the class before 
        its first use.  The tables are:
        1) NAME_MAP: map TempoType to string name.
        2) RANGE_MAP: map TempoType to BPM range.
        3) ALL_TYPES: list of all TempoTypes
        """
        if TempoTypeHelper.RANGE_MAP is not None:
            return

        TempoTypeHelper.RANGE_MAP = {
            TempoType.Larghissimo: Range(0, 24),
            TempoType.Grave: Range(25, 45),
            TempoType.Lento: Range(45, 60),
            TempoType.Largo: Range(40, 60),
            TempoType.Larghetto: Range(60, 66),
            TempoType.Adagio: Range(66, 76),
            TempoType.Adagietto: Range(72, 76),
            TempoType.Andantino: Range(80, 108),
            TempoType.Andante: Range(76, 108),
            TempoType.AndanteModerato: Range(92, 112),
            TempoType.MarciaModerato: Range(83, 85),
            TempoType.Moderato: Range(108, 120),
            TempoType.AllegroModerato: Range(116, 120),
            TempoType.Allegretto: Range(112, 120),
            TempoType.Allegro: Range(120, 168),
            TempoType.Vivace: Range(168, 176),
            TempoType.Vivacissimo: Range(172, 176),
            TempoType.Allegrissimo: Range(172, 176),
            TempoType.Presto: Range(168, 200),
            TempoType.Prestissimo: Range(200, 10000)
        }

        TempoTypeHelper.ALL_TYPES = [
            TempoType.Larghissimo,
            TempoType.Grave,
            TempoType.Lento,
            TempoType.Largo,
            TempoType.Larghetto,
            TempoType.Adagio,
            TempoType.Adagietto,
            TempoType.Andantino,
            TempoType.Andante,
            TempoType.AndanteModerato,
            TempoType.MarciaModerato,
            TempoType.Moderato,
            TempoType.AllegroModerato,
            TempoType.Allegretto,
            TempoType.Allegro,
            TempoType.Vivace,
            TempoType.Vivacissimo,
            TempoType.Allegrissimo,
            TempoType.Presto,
            TempoType.Prestissimo,
        ]
    
    def get_range(self):
        return TempoTypeHelper.RANGE_MAP[self]
    
    @staticmethod
    def get_types():
        return TempoTypeHelper.ALL_TYPES
    
    @staticmethod
    def get_range_for(tempo_type):
        """
        Static method to get the range for a tempo type.
        Args:
          tempo_type: if integer, turned into TempoType based on int.  Otherwise must be a TempoType.
          
        Returns: Range for type.
        Exception: on bad argument type.
        """
        if isinstance(tempo_type, int):
            tempo_type = TempoType(tempo_type)
        elif not isinstance(tempo_type, TempoType):
            raise Exception('Illegal argument type for get_range_for {0}'.format(type(tempo_type)))
        return TempoType.get_range(tempo_type)


# Initialize the static tables in the TempoType class.   
TempoType.class_init()

# ============================================================================== 
class Tempo(object):
    """
    Class that encapsulates the concept of tempo.
    Tempo is measured in BPM (beats per minute).
    self.__tempo holds the BPM.
    The value of the beat itself is determined by a time signature.
    
    Args:
      tempo:  the int or float value for the tempo
      beat_duration: the duration of the representative beat.  Usually 
                     implicitly the same as the time signature.  Here, the default is a quarter note,
                     but for compound signatures may be given as other than the beat value of a time signature.
                     e.g 12:8 may be 3/8 duration.
    """
    
    def __init__(self, tempo, beat_duration=Duration(1, 4)):
        if isinstance(tempo, int) or isinstance(tempo, float) or isinstance(tempo, Fraction):
            self.__tempo = tempo
        elif isinstance(tempo, TempoType):
            r = tempo.get_range()
            self.__tempo = int((r.end_index + r.start_index) / 2)
        else:
            raise Exception('Tempo rate can only use types int, float, or TempoType, not {0}'.format(type(tempo)))
        self.__beat_duration = beat_duration  
        
    @property
    def beat_duration(self):
        return self.__beat_duration 
    
    def effective_tempo(self, duration):
        """
        Convert the tempo relative to a new beat duration that maintains the same tempo rate for
        the original tempo.  e.g. 50 BMP for a 1/4 note == 100 BPM for an 1/8 note.
        
        Args: 
          duration: a Duration for the new beat value
          
        Returns:
          the new tempo as a float
        """
        return float(Fraction(self.tempo) * self.beat_duration.duration / duration.duration)
        
    @property
    def tempo(self):
        return self.__tempo

    def __str__(self):
        # return str(self.tempo)
        return 'Tempo[{0}, {1}]'.format(self.tempo, self.beat_duration)

# ==============================================================================
class TSBeatType(Enum):
    Whole = 1
    Half = 2
    Quarter = 3
    Eighth = 4
    Sixteenth = 5

    def __str__(self):
        return self.name

    def to_fraction(self):
        if self == TSBeatType.Whole:
            return Fraction(1, 1)
        if self == TSBeatType.Half:
            return Fraction(1, 2)
        if self == TSBeatType.Quarter:
            return Fraction(1, 4)
        if self == TSBeatType.Eighth:
            return Fraction(1, 8)
        if self == TSBeatType.Sixteenth:
            return Fraction(1, 16)

    @staticmethod
    def get_fraction_for(ts_beat_type):
        """
        Static method to get beat fraction value for a ts beat type.
        Args:
          ts_beat_type: if integer, turned into TSBeatType based on int.  Otherwise must be a TSBeatType.

        Returns: Range for type.
        Exception: on bad argument type.
        """
        if isinstance(ts_beat_type, int):
            ts_beat_type = TSBeatType(ts_beat_type)
        elif not isinstance(ts_beat_type, TSBeatType):
            raise Exception('Illegal argument type for get_fraction_for {0}'.format(type(ts_beat_type)))
        return ts_beat_type.to_fraction()

# ==============================================================================
class BeatType(Enum):
    """
    Enum to provide characterization of beat as strong or weak.
    """
    Strong = 'S'
    Weak = 'W'

    @staticmethod
    def to_beat_type(ltr):
        if ltr == 'S':
            return BeatType.Strong
        if ltr == 'W':
            return BeatType.Weak
        else:
            raise Exception('Illegal BeatType designation \'{0}\''.format(ltr))

# ==============================================================================
class TimeSignature(object):
    """
    Class representation of time signature.
    self.__beats_per_measure: number of beats per measure
    self.__beat_duration: holds the whole-note value (fraction) for the beat duration.
    self.__beat_pattern: string of S, B's length beats_per_measure indicating strong/weak beats (optional)
    """

    S = 'S'  # Strong beat designation
    W = 'W'  # Weak beat designation

    def __init__(self, beats_per_measure, beat_duration, beat_pattern=None):
        """
        Constructor
        Args 
          [0] beats_per_measure (int)
          [1] beat_duration (Fraction, int, Duration, TSBeatType)
          
        When TSBeatType is specified for beat duration, its fraction value is retained only.
        """
 #       from timemodel.duration import Duration

        if not isinstance(beats_per_measure, int):
            raise Exception('First argument of time signature must be integer')
        self.__beats_per_measure = beats_per_measure
        if isinstance(beat_duration, Fraction):
            self.__beat_duration = Duration(beat_duration)
        elif isinstance(beat_duration, int):
            self.__beat_duration = Duration(Fraction(beat_duration, 1))
        elif isinstance(beat_duration, TSBeatType):
            self.__beat_duration = Duration(beat_duration.to_fraction())
        elif isinstance(beat_duration, Duration):
            self.__beat_duration = beat_duration
        else:
            raise Exception("Second argument of time signature illegal type {0}".format(type(beat_duration)))

        if beat_pattern is not None:
            if not isinstance(beat_pattern, str):
                raise Exception("Beat pattern must be string, not {0}.".format(type(beat_pattern)))
            bp = beat_pattern.upper()
            if len(bp) != beats_per_measure:
                raise Exception("beat pattern must match beats_per_measure as length {0}.".format(beats_per_measure))
            for bt in bp:
                if bt != TimeSignature.S and bt != TimeSignature.W:
                    raise Exception('Beat pattern must only contain \'S\' or \'W\'')
            self.__beat_pattern = bp
        else:
            self.__beat_pattern = None
        
    @property
    def beats_per_measure(self):
        return self.__beats_per_measure
    
    @property
    def beat_duration(self):
        return self.__beat_duration

    @property
    def beat_pattern(self):
        return self.__beat_pattern

    def beats_matching(self, beat_type):
        beat_list = list()
        ltr = beat_type.value
        for i in range(0, len(self.beat_pattern)):
            if self.beat_pattern[i] == ltr:
                beat_list.append(i)
        return beat_list

    def beat_type(self, beat_index):
        if self.beat_pattern is None:
            return None
        if beat_index >= self.beats_per_measure:
            return None
        return BeatType.to_beat_type(self.beat_pattern[beat_index])
    
    def __str__(self):
        return 'TS[{0}, {1}]'.format(self.beats_per_measure, self.beat_duration)


# ==============================================================================
class Event(object):
    """
    Defines the Event class, being member to event_sequence. 
    """

    def __init__(self, objct, time):
        """
        Constructor.
        
        Args:
          objct:  Any object
          time:  An comparable usually representing time, i.e. must define __eq__ and __lt__.
        """
        self.__object = objct
        self.__time = time
        
        if time is None:
            raise Exception('Attempt to define an event without a time element')
        
    @property
    def object(self):
        return self.__object
    
    @object.setter
    def object(self, new_object):
        self.__object = new_object
    
    @property
    def time(self):
        """
        Should not be exposed to the user, and must me used with care, e.g. if part of an event sequence,
        the sequence time should be coordinated.
        """
        return self.__time
    
    @time.setter
    def time(self, new_time):
        self.__time = new_time
    
    def __str__(self):
        return '[{0}, {1}]'.format(self.time, self.object)

# ==============================================================================
class TimeSignatureEvent(Event):
    """
    Defines a time signature as an Event.
    """

    def __init__(self, time_signature, time):
        """
        Constructor.
        
        Args:
          time_signature: (TimeSignature) object.
          time: Position.
        """
        if not isinstance(time, Position):
            raise Exception('time argument to TimeSignatureEvent must be Position not \'{0}\'.'.format(type(time)))
        Event.__init__(self, time_signature, time)

    def time_signature(self):
        return self.object.time_signature

    def __str__(self):
        return '[{0}, TimeSignature({1})]'.format(self.time, self.object)


# ==============================================================================
class TempoEvent(Event):
    """
    Defines tempo as an Event, given a Tempo and a time position.
    """

    def __init__(self, tempo, time):
        """
        Constructor.
        
        Args:
          tempo:(Tempo) object.
          time: Postion.
        """
        if not isinstance(time, Position):
            raise Exception('time argument to TempoEvent must be Position not \'{0}\'.'.format(type(time)))
        Event.__init__(self, tempo, time)

    def tempo(self):
        return self.object.tempo
    
    def __str__(self):
        return '[{0}, Tempo({1})]'.format(self.time, self.object)

# ==============================================================================
class OrderedMap(object):
    """
    OrderedMap defines a dict whose key is ordered.
    """
    
    def __init__(self, inputt=None):
        """
        Constructor
        Args:
           inputt: A list or dict or OrderedMap.
        """
        if inputt is not None:
            if isinstance(inputt, list):
                self.od = OrderedDict(sorted(inputt, key=lambda t: t[0]))
                self.reverse_dict = {value: key for (key, value) in inputt}
            elif isinstance(inputt, dict) or isinstance(inputt, OrderedMap):
                self.od = OrderedDict(sorted(inputt.items(), key=lambda t: t[0]))
                self.reverse_dict = {value: key for (key, value) in inputt.items()}
            else:
                raise Exception('Cannot construct OrderedMap from type {0}'.format(type(inputt)))
        else:
            self.od = OrderedDict()
            self.reverse_dict = {}
            
    def get(self, index):
        return self.od[index]
    
    def __getitem__(self, index):
        return self.od[index]

    def __len__(self):
        return len(self.od)
    
    def is_empty(self):
        return len(self.od) == 0
    
    def reverse_get(self, value):
        """
        For a given object value find the key value that maps to it. 
        """
        return self.reverse_dict[value]
    
    def has_reverse(self, value):
        return value in self.reverse_dict
    
    def has_key(self, key):
        return key in self.od

    def __contains__(self, key):
        return key in self.od
    
    def keys(self):
        return self.od.keys()
    
    def insert(self, index, value):
        self.od[index] = value
        self.od = OrderedDict(sorted(self.od.items(), key=lambda t: t[0]))
        self.reverse_dict[value] = index
        
    def merge(self, inputt):
        """
        Merge a list of tuples, list, or OrderedMap.
        
        Args:
          inputt: A tuple list, dict, or OrderedMap.
          
        Returns:
          An OrderedMap that holding entries, a combination of self and inputt.
        """
        if inputt is not None:
            if isinstance(inputt, list):
                temp = dict(inputt)
                temp.update(self.od)
                self.od = OrderedDict(sorted(temp.items(), key=lambda t: t[0]))
                for i in inputt:
                    self.reverse_dict[i[1]] = i[0]
            elif isinstance(inputt, dict) or isinstance(inputt, OrderedMap):
                temp = inputt.copy()
                temp.update(self.od)
                self.od = OrderedDict(sorted(temp.items(), key=lambda t: t[0]))
                for i in inputt.items():
                    self.reverse_dict[i[1]] = i[0]
            else:
                raise Exception('Cannot merge OrderedMap from type {0}'.format(type(inputt)))  
            
    def copy(self):
        return OrderedMap(list(self.od.items()))
    
    def update(self, other_dict):
        self.od.update(other_dict) 
        self.od = OrderedDict(sorted(self.od.items(), key=lambda t: t[0]))
        for i in other_dict.items():
            self.reverse_dict[i[1]] = i[0]
        
    def remove_key(self, key):
        if key in self.od:
            value = self.od[key]
            del self.od[key]
            del self.reverse_dict[value]

    def clear(self):
        self.od = OrderedDict()
        self.reverse_dict = {}        
        
    def items(self):
        """
        Return all items in the ordered dictionary, each in tuple form (key, value).
        :return:
        """
        return self.od.items()

    def value_items(self):
        """
        Return all items in the ordered dictionary, but only the value in same order as self.items().
        :return:
        """
        return [x[1] for x in self.items()]

    def floor(self, key):
        # return key of od that is highest key less than given key argument.
        key_index = self.floor_calc(key)
        if key_index is None:
            return None

        alist = list(self.od.keys())
        return alist[key_index]

    def ceil(self, key):
        key_index = self.floor_calc(key)

        alist = list(self.od.keys())
        if key_index is None:
            if self.is_empty():
                return None
            if key < alist[0]:
                return alist[0]
            if key_index == len(alist) - 1:
                return None
        return None if key_index >= len(alist) - 1 else alist[key_index + 1]

    #  Think of it as searching on N semi-closed intervals instead of searching on points.
    #  For N points there are N-1 sections., indexed 0 --> N-2,
    #       with the interval being represented by the lower point index.
    #  The critical test is seeing if 'item' is within the interval that starts with midpoint
    def floor_calc(self, key):
        """
        For a key find the highest map key less than the given key.
        
        Args:
          key: the input key for which we want to find the floor key in the map.
          
        Returns:
          the floor key, or None if none is found.
        """
        if self.is_empty():
            return None
                
        alist = list(self.od.keys())
        num_pts = len(alist)
        num_sections = num_pts - 1
   
        if key >= alist[num_pts - 1]:
            return num_pts - 1
        if key < alist[0]:
            return None
    
        first = 0
        last = num_sections - 1
        found = -1
    
        while first <= last and found == -1:
            midpoint = (first + last)//2
            if alist[midpoint + 1] > key >= alist[midpoint]:
                found = midpoint
                break
            if key < alist[midpoint]:
                last = midpoint-1
            else:
                first = midpoint+1
    
        return found
    
    def floor_entry(self, item):
        """
        For a key find the highest map key less than given key, and its mapped value.
        
        Args:
          item: the input key for which we want to find the floor key and the mapped value.
          
        Returns:
          (floor_key, mapped_value)  or (None, None) if floor fails.
        """
        floor_key = self.floor(item)  
        if floor_key is None:
            return None, None
        return floor_key, self.od[floor_key]

    def ceil_entry(self, item):
        """
        For a key find the lowest map key greater than given key, and its mapped value.

        Args:
          item: the input key for which we want to find the ceil key and the mapped value.

        Returns:
          (ceil_key, mapped_value)  or (None, None) if ceil fails.
        """
        ceil_key = self.ceil(item)
        if ceil_key is None:
            return None, None
        return ceil_key, self.od[ceil_key]
# ==============================================================================
class EventSequence(object):
    """
    A class to collect a sequence of Event's ordered (increasing) by the Event's time value.
    The class contains the following event accounting structures:
    1) OrderedMap: ordering the events by time in a map that provides a floor() function.
    2) successor: a dict that maps events to successors.
    3) predecessor: a dict that maps events to predecessors.
    4) first: first event in the event sequence.
    5) last: last event in the event sequence.
    """

    def __init__(self, event_list=None):
        """
        Constructor.
        
        Args:
          event_list:  Any of None, a single Event, or a list of Events.
        """
        self.ordered_map = OrderedMap()
        
        self._successor = {}
        self._predecessor = {}
        self.__first = None
        self.__last = None
        
        if event_list:
            self.add(event_list)
    
    @property       
    def sequence_list(self):
        return list(self.ordered_map.get(x) for x in self.ordered_map.keys())
    
    @property
    def is_empty(self):
        return self.ordered_map.is_empty()
    
    def floor(self, time):
        return self.ordered_map.floor(time)
    
    def event(self, index):
        return self.ordered_map.get(index)
    
    def floor_event(self, time):
        floor_position = self.floor(time)
        return self.event(floor_position) if floor_position else None
    
    @property
    def first(self):
        return self.__first
    
    @property
    def last(self):
        return self.__last
    
    def add(self, new_members):
        """
        Add any of a single Event or a list of Events.
        
        Args:
          new_members: Any of a single Event or a list of events
        """
                
        if isinstance(new_members, list):
            mem_set = new_members
            inputt = [(e.time, e) for e in new_members]

        else:
            mem_set = [new_members]
            inputt = [(new_members.time, new_members)]
           
        for m in mem_set:
            if self.ordered_map.has_reverse(m):
                raise Exception('{0} already a member of sequence.'.format(m))  
            if not isinstance(m, Event):
                raise Exception('{0} is not an event.'.format(m)) 
            
        for i in inputt:
            if i[1].time not in self.ordered_map:
                self._add_successor_predecessor_maps(i[1])
            else:
                self._update_successor_predecessor_maps(i[1])
            self.ordered_map.insert(i[0], i[1])                  
        
    def remove(self, members): 
        """
        Remove any of a single Event or a list of Events already in the sequence.
        
        Args:
          members: Any of a single Event or a list of Events already in the sequence.
        """
        if isinstance(members, list):
            for member in members:
                self.remove(member)
        else:
            if not self.ordered_map.has_reverse(members):
                raise Exception('{0} not a member of sequence'.format(members))            
            self._remove_successor_predecessor_maps(members)
            self.ordered_map.remove_key(self.ordered_map.reverse_get(members))  
            
    def move_event(self, event, new_time):
        """
        Method to move event in sequence to a new time.
        
        Args:
          event: (Event) to move
          new_time: the new time setting for the event
        """
        if self.event(event.time) != event:
            raise Exception('Given event at time {0} not in sequence'.format(event.time))
        self.remove(event)
        event.time = new_time
        self.add(event)
            
    def _add_successor_predecessor_maps(self, event):
        fl_key = self.floor(event.time)
        if fl_key:
            a = self.event(fl_key)
            b = self._successor[a]  # could be None  event is between a and b
            self._successor[a] = event
            self._successor[event] = b
            self._predecessor[event] = a
            if b:
                self._predecessor[b] = event
            else:
                self.__last = event
        else:  # this event has to come first
            if self.__first:
                self._successor[event] = self.__first
                self._predecessor[self.__first] = event
                self._predecessor[event] = None
                self.__first = event
            else:
                self.__first = self.__last = event
                self._successor[event] = None
                self._predecessor[event] = None
            
    def _update_successor_predecessor_maps(self, event):
        e = self.event(event.time)
        self.remove(e)
        self._add_successor_predecessor_maps(event)
        pass
    
    def _remove_successor_predecessor_maps(self, event):
        a = self._predecessor[event]
        b = self._successor[event]
        del self._successor[event]
        del self._predecessor[event]
        if a:
            self._successor[a] = b
        else:
            self.__first = b
        if b:
            self._predecessor[b] = a
        else:
            self.__last = a
        
    def clear(self):
        self.ordered_map.clear()
        self._successor.clear()
        self._predecessor.clear()
        
    def successor(self, event):
        return self._successor[event] if event in self._successor else None
    
    def predecessor(self, event):
        return self._predecessor[event] if event in self._predecessor else None
        
    def __str__(self):
        return ', '.join(str(x) for x in self.sequence_list)
    
    def print_maps(self):
        print('---------')
        if self.__first:
            print('first={0}'.format(self.__first))
        else:
            print('first=None')
        if self.__first:
            print('last={0}'.format(self.__last))
        else:
            print('last=None')
        
        print('Successor:')
        for i in self._successor.items():
            print('   {0} --> {1}'.format(i[0].object if i[0] else 'None', i[1].object if i[1] else 'None'))

        print('Predecessor:')
        for i in self._predecessor.items():
            print('   {0} --> {1}'.format(i[0].object if i[0] else 'None', i[1].object if i[1] else 'None'))

# ==============================================================================
class Element(object):
    
    def __init__(self, ts_or_tempo, position):
        self.__element = ts_or_tempo
        self.__is_tempo = isinstance(ts_or_tempo, Tempo)
        if not self.__is_tempo and not isinstance(ts_or_tempo, TimeSignature):
            raise Exception('Expecting Tempo or TimeSignature, not {0}'.format(type(ts_or_tempo)))
        
        self.__position = position
        self.__position_time = 0
        
    @property
    def element(self):
        return self.__element
    
    @property
    def is_tempo(self):
        return self.__is_tempo
    
    @property
    def position(self):
        return self.__position
        
    @property
    def position_time(self):
        return self.__position_time
    
    @position_time.setter
    def position_time(self, value):
        self.__position_time = value
        
    def is_ts(self):
        return not self.is_tempo
    
    def __str__(self):
        return 'Element({0}, {1}'.format(self.position, self.element)

# ==============================================================================
class TimeConversion(object):
    """
    Time conversion algorithms.
    1) Whole Time --> actual time
    2) actual time --> Wholec Time
    """

    def __init__(self, tempo_line, ts_line, max_position, pickup=Duration(0, 1)):
        """
        Constructor.
        
        Args:
          tempo_line: (EventSequence) of TempoEvent's
          ts_line: (EventSequence) of TimeSignatureEvent's
          max_position: Position of end of whole note time
          pickup: whole note time for a partial initial measure
          
        Assumption:
          tempo_line and ts_line cover position 0
          
        Exceptions:
          If pickup exceeds whole note time of the first time signature.
        """
        self.tempo_line = tempo_line
        self.ts_line = ts_line
        self.__max_position = max_position
        self.__pickup = pickup

        if not isinstance(max_position, Position):
            raise Exception('max_position argument must be Position not \'{0}\'.'.format(type(max_position)))
        
        # check if the pickup exceeds the first TS
        if self.ts_line is None or self.ts_line.is_empty or self.tempo_line is None or self.tempo_line.is_empty:
            raise Exception('Time Signature and Tempo sequences must be non-empty for time conversions.')
        if pickup.duration >= self.ts_line.event(0).object.beats_per_measure * \
                self.ts_line.event(0).object.beat_duration.duration:
            raise Exception(
                'pickup exceeds timing based on first time signature {0}'.format(self.ts_line.event(0).object))
        
        self._build_uniform_element_list()
        self._build_lines()
        self._build_search_trees()
        
        self.__max_time = self.position_to_actual_time(self.max_position)
        
    @property
    def max_position(self):
        return self.__max_position
    
    @property
    def pickup(self):
        return self.__pickup
        
    @property
    def max_time(self):
        return self.__max_time
        
    def _build_uniform_element_list(self):
        self.element_list = [Element(x.object, x.time) for x in self.tempo_line.sequence_list] + \
                            [Element(x.object, x.time) for x in self.ts_line.sequence_list]
        self.element_list.sort(key=lambda p: p.position)
        
    def _build_lines(self):
        """
        Compute the actual time for the tempo and time signature elements.
        """
        current_ts = None
        current_tempo = None
        current_at = 0
        last_position = None
        
        for element in self.element_list:
            if current_ts and current_tempo:
                translated_tempo = current_tempo.effective_tempo(current_ts.beat_duration)
                current_at += (element.position - last_position).duration / \
                              (current_ts.beat_duration.duration * translated_tempo) * 60 * 1000
                element.position_time = current_at
                
            if element.is_tempo:
                current_tempo = element.element
            else:
                current_ts = element.element
            last_position = element.position
            
    def _build_search_trees(self):
        ts_mt_list = []
        ts_time_list = []
        tempo_mt_list = []
        tempo_time_list = []
        
        for element in self.element_list:
            if element.is_tempo:
                tempo_mt_list.append((element.position, element.element))
                tempo_time_list.append((element.position_time, element.element))
            else:
                ts_mt_list.append((element.position, element.element))
                ts_time_list.append((element.position_time, element.element))
                
        self.ts_mt_map = OrderedMap(ts_mt_list)    # whole note time --> TimeSignature
        self.ts_time_map = OrderedMap(ts_time_list)   # actual time --> TimeSignature

        self.tempo_mt_map = OrderedMap(tempo_mt_list)  # whole note time to Tempo
        self.tempo_time_map = OrderedMap(tempo_time_list)   # actual time to Tempo
        
        # Build an ordered map, mapping BeatPosition --> time signature.
        ts_bp_list = []
        (position, ts) = ts_mt_list[0]
        prior_pickup = 0
        measure_tally = 0
        if self.pickup.duration > 0:
            num_beats = self.pickup.duration / ts.beat_duration.duration
            ts_bp_list.append((BeatPosition(0, ts.beats_per_measure - num_beats), ts))
            prior_pickup = num_beats
        else:
            ts_bp_list.append((BeatPosition(0, Fraction(0, 1)), ts))           
        
        for i in range(1, len(ts_mt_list)):
            (position, ts) = ts_mt_list[i]
            (prior_position, prior_ts) = ts_mt_list[i - 1]
            num_beats = (position - prior_position).duration / prior_ts.beat_duration.duration - prior_pickup
            num_measures = int(num_beats / prior_ts.beats_per_measure) + (1 if prior_pickup > 0 else 0)
            measure_tally += num_measures
            prior_pickup = 0
            ts_bp_list.append((BeatPosition(measure_tally, 0), ts))
        self.ts_bp_map = OrderedMap(ts_bp_list)    # beat position --> TimeSignature    

    def position_to_actual_time(self, position):
        """
        Convert a whole time position to it's actual time (in ms) from the beginning.
        
        Args:
          position: a Position in whole time.
        Returns:
          The actual time in ms for the position relative to the beginning.
          
        Note: if the position exceeds max_position, we use max_position
        """
        (tempo_mt_floor, tempo_element) = self.tempo_mt_map.floor_entry(position)
        tempo_time = self.tempo_time_map.reverse_get(tempo_element)
        
        (ts_mt_floor, ts_element) = self.ts_mt_map.floor_entry(position)
        ts_time = self.ts_time_map.reverse_get(ts_element)
        
        start_mt = max(tempo_mt_floor, ts_mt_floor)
        start_time = max(tempo_time, ts_time)
        # at this point, we have:
        #  start_mt: a whole time to start from
        #  start_time: the actual time to start from
        #  tempo_element: the current Tempo
        #  ts_element: the current TimeSignature
        
        delta_mt = min(position, self.max_position) - start_mt
        translated_tempo = tempo_element.effective_tempo(ts_element.beat_duration)
        # time = music_time / (beat_duration * tempo)
        delta_time = (delta_mt.duration / (ts_element.beat_duration.duration * translated_tempo)
                      if delta_mt > 0 else 0) * 60 * 1000
      
        return start_time + delta_time
     
    def actual_time_to_position(self, actual_time):  
        """
        Convert from an actual time (ms) position to a whole time Position
        
        Args:
          actual_time: the actual time (ms) of a position in the music
        Returns:
          the Position corresponding to the actual time.
          
        Note: if actual_time exceeds max_time, we use max_time.
        """
        (tempo_time_floor, tempo_element) = self.tempo_time_map.floor_entry(actual_time)
        tempo_mt = self.tempo_mt_map.reverse_get(tempo_element)
        (ts_time_floor, ts_element) = self.ts_time_map.floor_entry(actual_time)
        ts_mt = self.ts_mt_map.reverse_get(ts_element)
        
        start_mt = max(tempo_mt, ts_mt)
        start_time = max(tempo_time_floor, ts_time_floor)
        # at this point, we have:
        #  start_mt: a whole note time to start from
        #  start_time: the actual time to measure from
        #  tempo_element: the current Tempo
        #  ts_element: the current TimeSignature
        
        delta_time = min(actual_time, self.max_time) - start_time
        if not isinstance(delta_time, Fraction):
            delta_time = Fraction.from_float(delta_time)
        # musicTime = time * tempo * beat_duration
        # Translate tempo using the time signature beat.
        translated_tempo = tempo_element.effective_tempo(ts_element.beat_duration)
        delta_mt = (delta_time * translated_tempo * ts_element.beat_duration.duration / (60 * 1000)) \
            if delta_time > 0 else 0
        
        return start_mt + delta_mt
    
    def bp_to_position(self, beat_position):
        """
        Method to convert a beat position to a whole note time position.
        
        Args:
          beat_position: BeatPosition object given measure, beat number
        Returns:
          the whole note time position for beat_position.
          
        Exceptions:
          for improper beat_position values
        """
        (beginning_bp, ts_element) = self.ts_bp_map.floor_entry(beat_position)
        if beat_position.beat_number >= ts_element.beats_per_measure:
            raise Exception(
                'Illegal beat asked for {0}, ts has 0-{1} beats per measure.'.format(beat_position.beat_number,
                                                                                     ts_element.beats_per_measure - 1))
        
        ts_mt_floor = self.ts_mt_map.reverse_get(ts_element)
        
        delta_mt = ((beat_position.measure_number - beginning_bp.measure_number) * ts_element.beats_per_measure +
                    beat_position.beat_number - beginning_bp.beat_number) * ts_element.beat_duration.duration
        return Position(ts_mt_floor.position + delta_mt)
    
    def position_to_bp(self, position):
        """
        Method to convert a whole note time position to a beat position
        
        Args:
          position: the whole note time position
        Returns:
          the BeatPosition corresponding to the given position
        """
        (ts_mt_floor, ts_element) = self.ts_mt_map.floor_entry(position)
        
        ts_bp = self.ts_bp_map.reverse_get(ts_element)
        
        num_beats = (position - ts_mt_floor).duration / ts_element.beat_duration.duration   # - prior_pickup.duration
        num_measures = int(num_beats / ts_element.beats_per_measure)   # + (1 if prior_pickup.duration > 0 else 0)
        residual_beats = num_beats - num_measures * ts_element.beats_per_measure
        
        # add the measures and beats  to ts_bp
        beats = ts_bp.beat_number + residual_beats
        measures = ts_bp.measure_number + num_measures
        if beats >= ts_element.beats_per_measure:
            beats -= ts_element.beats_per_measure
            measures += 1
                    
        return BeatPosition(measures, beats)

# ==============================================================================
# ============================================================================== 9
# ==============================================================================

class AbstractNote(object):
    """
    A root class for all note and note grouping classes.
    
    The following are properties
    parent: The parent of an AbstractNote within an AbstractNote hierarchy, ref. AbstractNoteCollective.
    relative_position: A Position noting the whole note time onset of the note in it immediate collection.
    contextual_reduction_factor: The multiplicative factor imposed by a structure downward in the hierarchy.
    """
    
    NOTES_ADDED_EVENT = 'Notes added to line'
    NOTES_REMOVED_EVENT = 'Notes removed from line'
    
    __metaclass__ = ABCMeta

    def __init__(self):
        self.__parent = None
        self.__relative_position = Offset(0)
        self.__contextual_reduction_factor = Fraction(1)
    
    @property
    def parent(self):
        return self.__parent
        
    @parent.setter
    def parent(self, parent):
        self.__parent = parent
        
    @property
    def relative_position(self):
        return self.__relative_position
    
    @relative_position.setter
    def relative_position(self, relative_position):
        self.__relative_position = relative_position
        
    @property
    def contextual_reduction_factor(self):
        return self.__contextual_reduction_factor
    
    @contextual_reduction_factor.setter
    def contextual_reduction_factor(self, contextual_reduction_factor):
        self.__contextual_reduction_factor = contextual_reduction_factor        
                
    @property
    def duration(self):
        raise NotImplementedError('define duration in subclass to use this base class')
    
    def reverse(self):
        raise NotImplementedError('users must define reverse() to use this base class')
    
    def get_original_parent(self):
        p = self.parent
        last_known_parent = p
        
        while True:
            if p is None:
                return last_known_parent
            last_known_parent = p
            p = p.parent
            
    def get_absolute_position(self):
        """
        Find the absolute position of this abstract note in its contextual tree
        """
        n = self
        p = Position(0)
        while True:
            p += n.relative_position
            n = n.parent
            if n is None:
                break
        return p           
           
    @abstractmethod
    def get_all_notes(self):
        raise NotImplementedError('users must define get_all_notes to use this base class')
    
    @staticmethod
    def print_structure(note, indent=0):
  #      from structure.note import Note    FATTO
  #      from structure.beam import Beam    FATTO
  #      from structure.beam import Tuplet  FATTO
  #      from structure.line import Line    FATTO
        if isinstance(note, Note):
            print('{0}Note {1} off {2} f={3} {4}'.format(indent*' ', str(note), note.relative_position,
                                                         note.contextual_reduction_factor,
                                                         'T' if note.is_tied_to else ''))
        elif isinstance(note, Beam):
            print('{0}Beam dur {1} off {2} f={3}'.format(indent*' ', note.duration, note.relative_position,
                                                         note.contextual_reduction_factor))
            for n in note.sub_notes:
                AbstractNote.print_structure(n, indent + 4)
        elif isinstance(note, Tuplet):
            print('{0}Tuplet dur {1} off {2} f={3}'.format(indent*' ', note.duration, note.relative_position,
                                                           note.contextual_reduction_factor))
            for n in note.sub_notes:
                AbstractNote.print_structure(n, indent + 4)
        elif isinstance(note, Line):
            print('{0}Line dur {1} off {2} f={3}'.format(indent*' ', note.duration, note.relative_position,
                                                         note.contextual_reduction_factor))
            for n in note.sub_notes:
                AbstractNote.print_structure(n, indent + 4)
        else:
            print('unknown type {0}'.format(type(note)))

    def clone(self):
    #    from structure.beam import Beam
    #    from structure.tuplet import Tuplet
    #    from structure.note import Note
    #    from structure.line import Line
    #    from timemodel.duration import Duration
        cpy = None
        if isinstance(self, Beam):
            cpy = Beam()
            for s in self.sub_notes:
                s_prime = s.clone()
                cpy.append(s_prime)
        elif isinstance(self, Tuplet):
            cpy = Tuplet(self.unit_duration, self.unit_duration_factor)
            for s in self.sub_notes:
                s_prime = s.clone()
                cpy.append(s_prime)
        elif isinstance(self, Note):
            d = Duration(self.base_duration.duration / self.contextual_reduction_factor)
            cpy = Note(self.diatonic_pitch if self.diatonic_pitch is not None else None, d, self.num_dots)
        elif isinstance(self, Line):
            cpy = Line(None, self.instrument)
            for s in self.sub_notes:
                s_prime = s.clone()
                cpy.pin(s_prime, s.relative_position)

        return cpy

# ==============================================================================
class Note(AbstractNote):
    """
    Class representation for a musical note.
    """

    STANDARD_NOTES = {'W': Duration(1),
                      'H': Duration(1, 2),
                      'Q': Duration(1, 4),
                      'E': Duration(1, 8),
                      'S': Duration(1, 16),
                      'T': Duration(1, 32),
                      'X': Duration(1, 64),
                      }

    def __init__(self, diatonic_pitch,  base_duration, num_dots=0):
        """
        Constructor.
        
        Args
          diatontic_pitch: ref. class DiatonicPitch.
          base_duration: either a Duration, or key in STANDARD_NOTES (upper or lower case).
          num_dots: number of duration extension dots.
        """
        AbstractNote.__init__(self)
        
        self.__diatonic_pitch = diatonic_pitch
        self.__num_dots = num_dots
        if type(base_duration) == Duration:
            self.__base_duration = base_duration
        elif isinstance(base_duration, str):
            if base_duration.upper() in Note.STANDARD_NOTES.keys():
                self.__base_duration = Note.STANDARD_NOTES[base_duration.upper()]
            else:
                raise Exception('Base duration can only be a Duration or string in key set [w, h, q, e, s, t. x]')
        self.__duration = self.base_duration.apply_dots(num_dots)
        
        self.__tied_to = None
        self.__tied_from = None
        
    @property
    def diatonic_pitch(self):
        return self.__diatonic_pitch

    @diatonic_pitch.setter
    def diatonic_pitch(self, new_pitch):
        self.__diatonic_pitch = new_pitch
    
    @property
    def duration(self):
        return self.__duration
    
    @property 
    def base_duration(self):
        return self.__base_duration

    @base_duration.setter
    def base_duration(self, base_duration):
        self.__base_duration = base_duration
        self.__duration = self.base_duration.apply_dots(self.num_dots)
    
    @property
    def num_dots(self):
        return self.__num_dots
    
    @property
    def is_tied_to(self):
        return self.__tied_to is not None
    
    @property
    def is_tied_from(self):
        return self.__tied_from is not None
    
    @property
    def tied_to(self):
        return self.__tied_to
    
    @property
    def tied_from(self):
        return self.__tied_from
    
    @property
    def is_rest(self):
        return self.diatonic_pitch is None
    
    def get_all_notes(self): 
        return [self]
    
    def tie(self):
        """
        Tie this note to the next note.
        """
        original_parent = self.get_original_parent()
        if original_parent is None:
            raise Exception('Cannot tie note that has no parent')
        note = self.next_note()
        if note is None:
            raise Exception('No next note to tie to.')
        
        # notes must have the same pitch
        if note.diatonic_pitch != self.diatonic_pitch:
            raise Exception(
                'Tied notes require to have same pitch {0} != {1}'.format(self.diatonic_pitch, note.diatonic_pitch))
        
        self.__tied_to = note
        note.__tied_from = self
        
    def untie(self):
        if not self.is_tied_to:
            return
        
        self.__tied_to.__tied_from = None
        self.__tied_to = None
    
    def next_note(self):
        """
        Determine the successor Note within the context of the note structure parentage.
        
        Returns:
          The successor Note, or None if there is none, e.g. this is the last note.
        """
        child = self
        p = child.parent
        
        while True:
            if p is None:
                break
            next_str = p.get_next_child(child)
            if next_str is not None:
                if isinstance(next_str, Note):
                    return next_str
                else:
                    return next_str.get_first_note()
            else:
                child = p
                p = p.parent
        # At this point, we are the last note in the structure - there is no next
        return None
      
    def prior_note(self):
        """
        Determine the Note prior to this one within the context of the note structure parentage.
        
        Returns:
          The prior Note, or None is there is none, e.g. this is the first note.
        """
        child = self
        p = child.parent
        
        while True:
            if p is None:
                break
            next_str = p.get_prior_child(child)
            if next_str is not None:
                if isinstance(next_str, Note):
                    return next_str
                else:
                    return next_str.get_last_note()
            else:
                child = p
                p = p.parent
        # At this point, we are the last note in the structure - there is no next
        return None        
           
    def apply_factor(self, factor):
        self.__base_duration *= factor
        self.__duration *= factor
        self.relative_position *= factor
        self.contextual_reduction_factor *= factor
        
    def reverse(self):
        return self
    
    def __str__(self):
        dot_string = str(self.base_duration) + self.num_dots * '@'        
        return '[{0}<{1}>-({2}){3}] off={4} f={5}'.format(
            self.diatonic_pitch if self.diatonic_pitch is not None else 'R', dot_string, self.duration,
            'T' if self.is_tied_to else '', self.relative_position, self.contextual_reduction_factor)

# ==============================================================================
class Observable(object):
    """
    Implementation of observer in Observer pattern.  The class defines a means
    of notifying clients of changes to the observable, as calls to the observer's 
    'notification' method.
    """

    def __init__(self):
        """
        Constructor
        """
        self.observers = set()
        
    def register(self, observer):
        """
        Register the observer to the observable.
        
        Args:
          observer: instance of Observer that gets notification
        Note: gets added to observers list, and is user responsibility to remove.
        """
    #    from misc.observer import Observer
         
        if not isinstance(observer, Observer):
            raise Exception('Argument is not an observer')       
        if observer not in self.observers:
            self.observers.add(observer)
            
    def deregister(self, observer):
        """
        Deregister observer as observer.
        
        Args:
          observer: instance of Observer that is removed for notification
          
        """
    #    from misc.observer import Observer
                
        if not isinstance(observer, Observer):
            raise Exception('Argument is not an observer')
        try:
            self.observers.remove(observer)  
        except (KeyError, AttributeError):
            # invalid observer, or the observers cleared
            pass
        
    def deregister_all(self):
        """
        Deregister all observers.
        """
        while len(self.observers) != 0:
            self.deregister(self.observers.pop())
        
    def update(self, message_type, message=None, data=None):
        """
        update is called whenever an event of importance should be noted by 
        all the observable's clients.
        
        Args:
          message_type: (any type) a message indicating the type of event.
          message: (string) any associated message about the event.
          data: (any type) any associated data about the event.
        """
        for observer in self.observers:
            observer.notification(self, message_type, message, data)

# ==============================================================================
class Observer(object):
    """
    Observer (client) to an Observable
    """
    __metaclass__ = ABCMeta

    def __init__(self):
        """
        Constructor.
        """
 
    @abstractmethod
    def notification(self, observable, message_type, message=None, data=None):
        """
        The method an observer must implement that is called whenever an event of interest happens to the
        observable.
        
        Args:
          observable: (Observable) the observable issuing the notification.
          message_type: (any type) a message indicating the type of event.
          message: (string) any associated message about the event.
          data: (any type) any associated data about the event.
        """
        pass   

# ==============================================================================
class AbstractNoteCollective(AbstractNote, Observer, Observable):
    """
    This class is the root to classes that aggregate other abstract notes.  
    That attribute is self.sub_notes, a list of consecutive child notes to the collective.
    This in essence constructs a tree of notes.
    """

    def __init__(self):
        """
        Constructor
        """
        AbstractNote.__init__(self)
        
        Observable.__init__(self)
        Observer.__init__(self)
        
        self.sub_notes = []
        
    def cardinality(self):
        return len(self.sub_notes)
    
    def sub_notes(self):
        """
        Access a list of sub_notes
        
        Returns
          A new list containing the contents of self.sub_notes
          
          NOTE: fix, cannot treat as property due to note insertion (self.sub_notes.insert(...), but should 
                allow way to get a copy of self.sub_notes
        """
        lst = []
        lst.extend(self.sub_notes)
        return lst

    @property
    def duration(self):
        """
        This is effectively the same as length(), giving the length of the collection.
        However, Tuplet and Beam override this to do a simple summation of linearly layed out notes and subnotes.
                 The reason is that the layout algorithm of these subclasses cannot use the realtive_position
                 attribute as the algorithm determines that.
        """
        return self.length() 
     
    def length(self):
    #    from structure.note import Note
    #    from fractions import Fraction
    #    from misc.utility import convert_to_numeric
        d = Fraction(0)
        for n in self.sub_notes:
            d = max(d, convert_to_numeric(n.relative_position + (n.duration if isinstance(n, Note) else n.duration)))
        return Duration(d)
                  
    def downward_refactor_layout(self, incremental_factor):
        """
        Called by Tuplet, this method applies the incremental factor down the tree, adjusting 
        note duration accordingly.  At a Note, it calls apply_factor to make durational adjustments.
        Otherwise, it calls recursively.
        The method also rescales the relative positions of abstract notes.
        
        Args:
          incremental_factor: the multiplicative factor to apply downward.
        """
    #    from structure.note import Note
        
        self.contextual_reduction_factor *= incremental_factor
        relpos = Offset(0)
        for n in self.sub_notes:
            if isinstance(n, Note):
                n.apply_factor(incremental_factor)
            else:
                n.downward_refactor_layout(incremental_factor)
            n.relative_position = relpos
            relpos += n.duration
        
    def upward_forward_reloc_layout(self, abstract_note):   
        """
        Called by Beam on Beam content alteration, it climbs the tree upward and to the right.
        making relative position adjustments along the way.  It stops when it hits either a null parent
        or a tuplet.  Since tuplets will not change size, there is no need to proceed higher up the tree.
        However, at that top tuplet level, it is appropriate to call Tuplet.rescale() as the lower contents
        have changed and can affect the tuplet's rescaling factor.
        
        Args:
          abstract_note: the affected child note of self.sub_notes which causes the relocataion layout.
        """
    #    from structure.tuplet import Tuplet
        try:
            index = self.sub_notes.index(abstract_note)
        except ValueError:
            raise Exception('Could note location index for {0} in {1}'.format(abstract_note, type(self)))
        
        current_position = Offset(0) if index == 0 else \
            self.sub_notes[index - 1].relative_position + self.sub_notes[index - 1].duration
        for i in range(index, len(self.sub_notes)):
            self.sub_notes[i].relative_position = current_position
            current_position += self.sub_notes[i].duration
        
        # Once size no longer changes, no need to propagate
        if self.parent is not None and not isinstance(self.parent, Tuplet):
            self.parent.upward_forward_reloc_layout(self)
            
        if self.parent is not None and isinstance(self.parent, Tuplet):
            self.parent.rescale()
            
    def apply_factor(self, factor):
        """
        Recursively update the contextual reduction factor by a factor.
        This is typically called when a new note structure is added to an exiting structure to get the
        factors up to date.
        
        Args:
          factor: factor to be applied to self.contextual_reduction_factor.
        """
        for n in self.sub_notes:
            n.apply_factor(factor) 
        self.relative_position *= factor 
        self.contextual_reduction_factor *= factor            
            
    def get_all_notes(self):
        """
        Recursive method to get a list of all notes within a structure, in positional order.
        """
        notes = []    
        for abstract_note in self.sub_notes:
            notes.extend(abstract_note.get_all_notes())
                
        return notes
    
    def get_next_child(self, child):
        index = self.sub_notes.index(child)
        if index == -1:
            raise Exception('Could not find child {0} in collective {1}'.format(child, self))
        if index >= len(self.sub_notes) - 1:
            return None
        return self.sub_notes[index + 1]
    
    def get_prior_child(self, child):
        index = self.sub_notes.index(child)
        if index == -1:
            raise Exception('Could not find child {0} in collective {1}'.format(child, self))
        if index == 0:
            return None
        return self.sub_notes[index - 1]
    
    def get_first_note(self):
    #    from structure.note import Note
        if len(self.sub_notes) == 0:
            return None
        
        n = self.sub_notes[0]
        if isinstance(n, Note):
            return n
        return n.get_first_note()
    
    def get_last_note(self):
    #    from structure.note import Note
        if len(self.sub_notes) == 0:
            return None
        
        n = self.sub_notes[len(self.sub_notes) - 1]
        if isinstance(n, Note):
            return n
        return n.get_last_note()
    
    def reverse(self):
        # reverse recursively
        self.sub_notes.reverse()
        for n in self.sub_notes:
            n.reverse()
        
        # recompute the relative locations    
        current_position = Offset(0) 
        for n in self.sub_notes:
            n.relative_position = current_position
            current_position += n.duration
            
        # if we are at the top, parent == None, get all notes and reverse ties
        if self.parent is None:
            notes = self.get_all_notes()
            # see discussion why we cannot march forward nor backwards and just untie and tie.
            notes_to_tie = []
            for n in notes:
                if n.is_tied_to:
                    notes_to_tie.append(n.tied_to)
                    n.untie()
            for n in notes_to_tie:
                n.tie()
                
    @AbstractNote.parent.setter
    def parent(self, p):
        if self.parent:
            self.deregister(self.parent)    # make parent not observe me.
        AbstractNote.parent.fset(self, p)   # this calls AbstractNote.parent(self, p) setter.
        # super(AbstractNoteCollective, self.__class__).parent.fset(self, p)   Alternatively
        if self.parent:
            self.register(self.parent)      # make the parent observe me

    def notes_added(self, note_list):  
        self.update(AbstractNote.NOTES_ADDED_EVENT, None, note_list)
             
    def notification(self,  observable, message_type, message=None, data=None):
    #    from structure.line import Line
        if message_type == AbstractNote.NOTES_ADDED_EVENT:
            self.update(AbstractNote.NOTES_ADDED_EVENT, None, data)
        elif message_type == Line.LINE_NOTES_ADDED_EVENT:
            self.update(Line.LINE_NOTES_ADDED_EVENT, None, data)

# ==============================================================================
class Beam(AbstractNoteCollective):
    """
    Beam is a grouping operation, having a set scaling ratio of 1/2, but unbounded aggregate duration.
    
    The basic idea of a beam is that for a stand alone beam, you can only add Note's of duration 1/4 or less.  
    That duration is retained under the beam.  
    However when a beam is added to a beam, it takes an additional reduction factor of 1/2.
    
    Note that these factors aggregate multiplicatively through self.contextual_reduction_factor
    """
    
    FACTOR = Fraction(1, 2)
    NOTE_QUALIFIER_DURATION = Duration(1, 4)

    def __init__(self, abstract_note_list=None):
        """
        Constructor
        
        Args: 
          abstract_note_list: list of notes, beams, and tuplets to add consecutively under the beam.
        """
        AbstractNoteCollective.__init__(self)

        if abstract_note_list is None:
            abstract_note_list = list()
        self.append(abstract_note_list)
        
    @property
    def duration(self):
        """
        This is an override of AbstractNoteCollective.duration.
        Tuplet and Beam override this to do a simple summation of linearly laid out notes and sub-notes.
                 The reason is that the layout algorithm of these subclasses cannot use the relative_position
                 attribute as the algorithm determines that.
        """
        d = Duration(0)
        for note in self.sub_notes:
            d += note.duration
        return d    
       
    def append(self, notes):
        """
        Append a set of abstract notes to the beam
        
        Args:
          notes: either a list of notes or a single note to add to the beam.
        """
        if isinstance(notes, list):
            for n in notes:
                self.append(n)
            return
        elif isinstance(notes, Note) or isinstance(notes, AbstractNoteCollective):
            self.add(notes, len(self.sub_notes))
        
    def add(self, note, index):
        """
        Beams can only add less than 1/4 notes, and arbitrary beams and tuplets.
        Only added beams incur a reduction factor of 1/2
        For collective notes, always apply the factor.
        """
        if note.parent is not None:
            raise Exception('Cannot add note already assigned a parent')
        if index < 0 or index > len(self.sub_notes):
            raise Exception('add note, index {0} not in range[0, {1}]'.format(index, len(self.sub_notes)))

        if isinstance(note, Note):
            '''
            For standard notation, the following test should be made.
            However, the structure is quite general and can support other durations.
            For that reason, we opt to take out this check, which could be returned of only standard classic
            durations are supported.
            if note.base_duration >= Duration(1, 4):
                raise Exception(
                    "Attempt to add note with duration {0} greater than or equal to {1}".
                    format(note.duration, Beam.NOTE_QUALIFIER_DURATION))
            '''
            new_factor = self.contextual_reduction_factor
        elif isinstance(note, Beam):
            new_factor = self.contextual_reduction_factor * Beam.FACTOR
        elif isinstance(note, Tuplet):
            new_factor = self.contextual_reduction_factor
        else:
            raise Exception('illegal type {0}'.format(type(note)))
        
        self.sub_notes.insert(index, note)
        note.parent = self
        note.apply_factor(new_factor)
        # The following call will adjust layout from this point right upward
        self.upward_forward_reloc_layout(note)  
                       
        # see if prior note is tied, and if so, break the tie.
        first_note = note
        if not isinstance(note, Note):   
            first_note = note.get_first_note()
            # If empty beam or tuplet is added, there is nothing to look for in terms of ties.
            if first_note is None:
                return
        prior = first_note.prior_note()
        if prior is not None and prior.is_tied_to:
            prior.untie()  
         
        # notify up the tree of what has changed
        self.notes_added([note]) 
   
    def __str__(self):
        base = 'Beam(Dur({0})Off({1})f={2})'.format(self.duration, self.relative_position,
                                                    self.contextual_reduction_factor)
        s = base + '[' + (']' if len(self.sub_notes) == 0 else '\n')
        for n in self.sub_notes:
            s += '  ' + str(n) + '\n'
        s += ']' if len(self.sub_notes) != 0 else ''
        return s
    
# ==============================================================================
class Tuplet(AbstractNoteCollective):
    """
    Tuplet is a grouping operation having bounded duration but variable scale factor based on full content duration.
    The bounded duration is determined by two attributes;
    1) unit_duration: a Duration representing a base note value 
    2) unit_duration_factor: a numeric representing how many of the above the full duration should be.
    """

    def __init__(self, unit_duration, unit_duration_factor, abstract_note_list=None):
        """
        unit_duration x unit_duration_factor gives the full intended duration for the construct.
        tuplets have bounded duration but variable scale factor based on its contents 
        
        Args:
          unit_duration: a Duration representing a base note value, e.g. quarter note 
          unit_duration_factor: a numeric representing how many of the above the full duration should be.
          abstract_note_list: a list of abstract notes to append to the tuplet
          
        Note that these factors aggregate multiplicatively through self.contextual_reduction_factor (see rescale())
        """
        AbstractNoteCollective.__init__(self)
        
        self.__unit_duration = unit_duration
        self.__unit_duration_factor = unit_duration_factor

        if abstract_note_list is None:
            abstract_note_list = list()
        self.append(abstract_note_list)
        
    @property
    def unit_duration(self):
        return self.__unit_duration
    
    @property
    def unit_duration_factor(self):
        return self.__unit_duration_factor 
    
    @property
    def duration(self):
        """
        This is an override of AbstractNoteCollective.duration.
        Tuplet and Beam override this to do a simple summation of linearly layed out notes and subnotes.
                 The reason is that the layout algorithm of these subclasses cannot use the realtive_position
                 attribute as the algorithm determines that.
        """
        d = Duration(0)
        for note in self.sub_notes:
            d += note.duration
        return d      
       
    def append(self, notes):
        """
        Append one or a list of notest to the tuplet.

        :param notes: List or individual note
        :return:
        """
        if isinstance(notes, list):
            for n in notes:
                self.append(n)
            return
        elif isinstance(notes, Note) or isinstance(notes, AbstractNoteCollective):
            self.add(notes, len(self.sub_notes))
        
    def add(self, note, index):
        """
        Beams can only add less than 1/4 notes, and arbitrary beams and tuplets.
        Only added beams incur a reduction factor of 1/2
        For collective notes, always apply the factor.
        """
    #    from structure.beam import Beam
        if note.parent is not None:
            raise Exception('Cannot add note already assigned a parent')
        if index < 0 or index > len(self.sub_notes):
            raise Exception('add note, index {0} not in range[0, {1}]'.format(index, len(self.sub_notes)))
        
        if isinstance(note, Note):
            if note.base_duration >= 2 * self.unit_duration:
                raise Exception(
                    "Attempt to add note with duration {0} greater than or equal to {1}".format(note.duration,
                                                                                                2 * self.unit_duration))
        elif not isinstance(note, Beam) and not isinstance(note, Tuplet):
            raise Exception('illegal type {0}'.format(type(note)))
            
        self.sub_notes.insert(index, note)
        note.parent = self
        note.apply_factor(self.contextual_reduction_factor)
        self.rescale()
        
        # see if prior note is tied, and if so, break the tie.
        first_note = note
        if not isinstance(note, Note):   
            first_note = note.get_first_note()
            # If empty tuplet or beam added, not note to tie.
            if first_note is None:
                return
        prior = first_note.prior_note()   
        if prior is not None and prior.is_tied_to:
            prior.untie()  
            
        self.notes_added([note])  
        
    def rescale(self):
        """
        Rebuild the factors for the duration is right.
        Instead of setting the self.contextual_reduction_factor, we create an incremental factor that when applied to
        the contextual_reduction_factor give the correct new factor.
        This is preferred since the incremental can be applied downward the tree
        in a straight forward way, as a contextual adjustment multiplicative factor.
        """
        original_full_duration = self.duration.duration / self.contextual_reduction_factor 
        new_factor = self.unit_duration.duration * self.unit_duration_factor / original_full_duration  
        
        #  get the contextual reduction factor contribution the parent give to self.
        contrib = self.parent.contextual_reduction_factor if self.parent else 1
        orig_f = self.contextual_reduction_factor / contrib
        
        incremental_contextual_factor = new_factor / orig_f     # self.contextual_reduction_factor
        
        self.downward_refactor_layout(incremental_contextual_factor)            
   
    def __str__(self):
        base = 'Tuplet({0}x{1}Dur({2})Off({3})f={4})'.format(self.unit_duration, self.unit_duration_factor,
                                                             self.duration, self.relative_position,
                                                             self.contextual_reduction_factor)
        s = base + '[' + (']' if len(self.sub_notes) == 0 else '\n')
        for n in self.sub_notes:
            s += '  ' + str(n) + '\n'
        s += ']' if len(self.sub_notes) != 0 else ''
        return s
    
# ==============================================================================
class Line(AbstractNoteCollective):
    """
    Line is a grouping operation having unbounded duration and constant scaling factor 1.
    """
    
    LINE_NOTES_ADDED_EVENT = 'Line notes added to line'
    LINE_NOTES_REMOVED_EVENT = 'Line notes removed from line'

    def __init__(self, abstract_note_list=None, instrument=None):
        """
        Constructor
        
        Args: 
          abstract_note_list: list of or one of notes, beams, and tuplets to add consecutively under the line.
        """
        AbstractNoteCollective.__init__(self)
        
        self.__instrument = instrument
        
        # map note --> articulation setting
        self.articulation_map = {}

        # This is still dangerous.  We used to use append.
        # Problem when voice is called passing an arg, then Voice.pin is called before proper initialization.
        #    The issue is that Voice designer has to know NOT to pass an arg.  How to get around?
        if abstract_note_list:
            self.pin(abstract_note_list)
            
    @property
    def instrument(self):
        return self.__instrument
    
    @instrument.setter
    def instrument(self, new_instrument):
        self.__instrument = new_instrument
        
    @property
    def duration(self):
        return self.length()

    def append(self, note_structure):
        self.pin(note_structure, Offset(self.duration.duration))
                
    def pin(self, note_structure, offset=Offset(0)):
        """
        Given a note_structure (Line, Note, Tuplet, Beam), make it an immediate child to this line.
        If it is a list, the members are added in note sequence, with offset being adjusted appropriately.
        
        Args:
          note_structure: (List of Line, Note, Tuplet, Beam) to add
          offset:  (Offset), of the first in list or given structure.
        """

        if not isinstance(offset, Offset):
            raise Exception('Offset parameter in pin() must be of type Offset, not \'{0}\'.'.format(type(offset)))
        if isinstance(note_structure, list):
            for n in note_structure:
                self._append_note(n, offset)
                offset += n.duration
        else:
            self._append_note(note_structure, offset)
            
        # sort by relative offset    Pins can happen any where, this helps maintains some sequential order to the line 
        sorted(self.sub_notes, key=lambda n1: n1.relative_position)
            
        self.update(Line.LINE_NOTES_ADDED_EVENT, None, note_structure) 
            
    def _append_note(self, note, offset):
        if not isinstance(note, Beam) and not isinstance(note, Tuplet) and not isinstance(note, Note) \
                and not isinstance(note, Line):
            raise Exception('Cannot add instance of {0} to Line'.format(type(note)))
        self.sub_notes.append(note)
        note.parent = self 
        note.relative_position = offset 
        
    def _validate_(self, note):
        pass
        
    def unpin(self, note_structure):
        if isinstance(note_structure, list):
            for n in note_structure:
                self._remove_note(n)
        else:
            self._remove_note(note_structure)
            
        # sort by relative offset    Unpins can happen any where, this helps maintains some sequential order to the line 
        sorted(self.sub_notes, key=lambda n1: n1.relative_position)
            
        self.update(Line.LINE_NOTES_REMOVED_EVENT, None, note_structure) 
        
    def _remove_note(self, note):
        if not isinstance(note, Beam) and not isinstance(note, Tuplet) and not isinstance(note, Note) \
                and not isinstance(note, Line):
            raise Exception('Cannot remove instance of {0} to Line'.format(type(note)))
        if note not in self.sub_notes:
            raise Exception('Con only remove notes in line {0)'.format(note))
        self.sub_notes.remove(note)
        note.parent = None   
        
    def clear(self):
        notification_list = list(self.sub_notes)
        for note in notification_list:
            self.sub_notes.remove(note)
            note.parent = None 
        self.update(Line.LINE_NOTES_REMOVED_EVENT, None, notification_list)        
        
    def __str__(self):
        base = 'Line(Dur({0})Off({1})f={2})'.format(self.duration, self.relative_position,
                                                    self.contextual_reduction_factor)
        s = base + '[' + (']' if len(self.sub_notes) == 0 else '\n')
        for n in self.sub_notes:
            s += '  ' + str(n) + '\n'
        s += ']' if len(self.sub_notes) != 0 else ''
        return s
    
    def upward_forward_reloc_layout(self, abstract_note):
        pass

    def sub_line(self, sub_line_range=None):
        """
        Take a sub-range (time) of this line, and build a new line with notes that begins within that range
        :param sub_line_range: numeric interval to check for inclusion.
        :return: (sub-line, onset of original (Position), duration of sub-line)

        Note: The sub_line is not guaranteed to have the same length as the line, as sub_line is constructed only of
        the notes contained withing sub_line_range, starting with the first note found.
        """
        sub_line_range = IntervalN(Fraction(0), self.duration.duration) if sub_line_range is None else sub_line_range

        new_line = Line(None, self.instrument)

        first_position = None
        for s in self.sub_notes:
            s_excluded = Line._all_start_in(s, sub_line_range)
            if s_excluded == 1:
                if first_position is not None:
                    offset = Offset(s.get_absolute_position().position - first_position)
                else:
                    first_position = s.get_absolute_position().position
                    offset = Offset(0)
                s_prime = s.clone()
                new_line.pin(s_prime, offset)
            else:
                if s_excluded == -1:
                    raise Exception("Line range {0} must fully enclose sub-structures: {1}.".format(sub_line_range, s))

        return new_line, Position(first_position) if first_position is not None else Position(0), new_line.duration

    @staticmethod
    def _all_start_in(note_structure, sub_line_range):
        """
        See if all notes in note_structure start within range.
        :param note_structure:
        :param sub_line_range: Numeric interval to check for inclusion.
        :return: 1 if covers fully, 0 if fully excluded, -1 if partially excluded
        """
        notes = note_structure.get_all_notes()
        num_notes_excluded = 0
        for n in notes:
            if not sub_line_range.contains(n.get_absolute_position().position):
                num_notes_excluded = num_notes_excluded + 1
        return 1 if num_notes_excluded == 0 else 0 if num_notes_excluded == len(notes) else -1

# ==============================================================================
# ============================================================================== 10
# ==============================================================================
class Chord(object):
    """
    Chords have several key ingredients
    1) chord template
    2) diatonic tonality (sometimes not needed or set to None)
    3) chord type
    4) root_tone
    5) tones
    """
    
    __metaclass__ = ABCMeta

    def __init__(self, chord_template, diatonic_tonality=None):
        """
        Constructor
        Args
          chord_template: ChordTemplate behind the chord.
          diatonic_tonality: DiatonicTonality (optional) that could help define the chord, e.g. by scale + scale degree.
        """
        
        self.__chord_template = chord_template
        self.__diatonic_tonality = diatonic_tonality
        
    @property
    def chord_template(self):
        return self.__chord_template
    
    @property
    def diatonic_tonality(self):
        return self.__diatonic_tonality
    
    @property
    @abstractmethod
    def chord_type(self):
        raise Exception('Chord type subclass needs chord_type property') 
    
    @property
    @abstractmethod
    def root_tone(self):
        raise Exception('Chord type subclass needs root_tone property')
    
    @property
    @abstractmethod
    def tones(self):
        raise Exception('Chord type subclass needs tones property')
# ==============================================================================
class ChordTemplate(object):
    """
    This is a base class for all chord definitions.
    """
    
    SCALE_DEGREE_MAP = {
        'I': 1, 'i': 1,
        'II': 2, 'ii': 2,
        'III': 3, 'iii': 3,
        'IV': 4, 'iv': 4,
        'V': 5, 'v': 5,
        'VI': 6, 'vi': 6,
        'VII': 7, 'vii': 7,
        'VIII': 8, 'viii': 8,
        'IX': 9, 'ix': 9,
        'X': 10, 'x': 10,
        'XI': 11, 'xi': 11,
        'XII': 12, 'xii': 12,
    }
    
    SCALE_DEGREE_REVERSE_MAP = {
        1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII'
                                }
    __metaclass__ = ABCMeta
    
    def __init__(self):
        """
        Constructor
        """

    @abstractmethod
    def create_chord(self, diatonic_tonality=None):
        raise NotImplementedError('users must define create_chord to use this base class')

    @staticmethod
    @abstractmethod
    def parse(chord_string):
        raise NotImplementedError('users must define parse to use this base class')
    
    @staticmethod
    def generic_chord_template_parse(chord_txt):
        """
        Generic text parse into chord template.
        
        Args:
          chord_txt: String
        Returns:
          ChordTemplate or None if fails.
        """

        #  Try parsing chord text through known chord templates.
        #  If all fail, just return None.
    #    from harmonicmodel.secondary_chord_template import SecondaryChordTemplate, SecondaryChordException
        try:
            chord_template = SecondaryChordTemplate.parse(chord_txt)
            return chord_template
        except SecondaryChordException:
            pass
    #    from harmonicmodel.tertian_chord_template import TertianChordTemplate, TertianChordException
        try:
            chord_template = TertianChordTemplate.parse(chord_txt)
            return chord_template
        except TertianChordException:
            pass
    #    from harmonicmodel.secundal_chord_template import SecundalChordTemplate, SecundalChordException
        try:
            chord_template = SecundalChordTemplate.parse(chord_txt)
            return chord_template
        except SecundalChordException:
            pass
    #    from harmonicmodel.quartal_chord_template import QuartalChordTemplate
        try:
            chord_template = QuartalChordTemplate.parse(chord_txt)
            return chord_template
        except QuartalChordTemplate:
            return None     

# ==============================================================================
class SecondaryChordException(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)


class SecondaryChordTemplate(ChordTemplate):
    """
    Class representing the definition of a secondary chord.
    """

    SCALE_DEGREE = 'III|II|IV|VII|VI|V|I|iii|ii|iv|vii|vi|v|i'
    SCALE_DEGREE_NAME = 'ScaleDegree'
    SCALE_DEGREE_TAG = '?P<' + SCALE_DEGREE_NAME + '>'

    INITIAL_CHORD_TEXT_NAME = 'InitialChordText'
    INITIAL_CHORD_TEXT_TAG = '?P<' + INITIAL_CHORD_TEXT_NAME + '>'
    INITIAL_CHORD = '(' + INITIAL_CHORD_TEXT_TAG + '[^/]*)'

    DIATONIC_MODALITIES = '|'.join(DiatonicModality.diatonic_modality_types_as_string_array())
    DIATONIC_MODALITIES_NAME = 'DiatonicModality'
    DIATONIC_MODALITIES_TAG = '?P<' + DIATONIC_MODALITIES_NAME + '>'
    DIATONIC_MODALITY = '(' + DIATONIC_MODALITIES_TAG + DIATONIC_MODALITIES + ')'

    SECONDARY_BASIS = '(' + SCALE_DEGREE_TAG + SCALE_DEGREE + ')' + '(\\[' + DIATONIC_MODALITY + '\\])?'

    # full parse string and accompanying pattern for the secondary chord grammar.
    SECONDARY_CHORD_PARSE_STRING = INITIAL_CHORD + '/' + SECONDARY_BASIS + '$'
    SECONDARY_CHORD_PATTERN = re.compile(SECONDARY_CHORD_PARSE_STRING)

    def __init__(self, principal_chord_template, secondary_scale_degree, secondary_modality):
        """
        Constructor.
        
        Args:
        principal_chord_template: ChordTemplate for the numerator. 
        secondary_scale_degree: (int) which scale degree 1 --> 6.
        secondary_modality: Modality for the denominator if specified (None if not specified).
        """
        ChordTemplate.__init__(self)

        self.__principal_chord_template = principal_chord_template
        self.__secondary_scale_degree = secondary_scale_degree
        self.__secondary_modality = secondary_modality

    def __str__(self):
        return '{0}/{1}-{2}'.format(str(self.principal_chord_template),
                                    ChordTemplate.SCALE_DEGREE_REVERSE_MAP[self.secondary_scale_degree],
                                    self.secondary_modality)

    @property
    def principal_chord_template(self):
        return self.__principal_chord_template

    @property
    def secondary_scale_degree(self):
        return self.__secondary_scale_degree

    @property
    def secondary_modality(self):
        return self.__secondary_modality

    def create_chord(self, diatonic_tonality=None):
        return SecondaryChord(self, diatonic_tonality)

    @staticmethod
    def parse(chord_string):
        """
        Parse an input string into a TertialChordTemplate.
        
        Args:
          chord_string: string input representing chord
        Returns:
          TertianChordTemplate       
        """
        if not chord_string:
            raise Exception('Unable to parse chord string to completion: {0}'.format(chord_string))
        m = SecondaryChordTemplate.SECONDARY_CHORD_PATTERN.match(chord_string)
        if not m:
            raise SecondaryChordException('Unable to parse chord string to completion: {0}'.format(chord_string))

        principal_chord_text = m.group(SecondaryChordTemplate.INITIAL_CHORD_TEXT_NAME)

        secondary_scale_degree_text = m.group(SecondaryChordTemplate.SCALE_DEGREE_NAME)
        secondary_scale_degree = ChordTemplate.SCALE_DEGREE_MAP[secondary_scale_degree_text]

        secondary_modality_text = m.group(SecondaryChordTemplate.DIATONIC_MODALITIES_NAME)
        secondary_modality = ModalityType(secondary_modality_text) if secondary_modality_text else None

        principal_chord_template = ChordTemplate.generic_chord_template_parse(principal_chord_text)
        if not principal_chord_template:
            raise SecondaryChordException('Unable to parse principle chord in secondary template: {0}'.
                                          format(principal_chord_text))

        logging.info('{0}, {1}, {2}, {3}'.format(principal_chord_text,
                                                 str(principal_chord_template),
                                                 secondary_scale_degree,
                                                 str(secondary_modality) if secondary_modality else ''))

        return SecondaryChordTemplate(principal_chord_template, secondary_scale_degree, secondary_modality)
    
# ==============================================================================
class SecondaryChord(Chord):
    """
    Represents and instance of a secondary chord.
    """

    def __init__(self, secondary_chord_template, diatonic_tonality, secondary_tonality=None):
        """
        Constructor.
        :param secondary_chord_template: SecondaryChordTemplate
        :param diatonic_tonality: DiatonicTonality (used in scale degree chord formation)
        :param secondary_tonality: Used to represent denominator tonality
        Note: The means for determining the secondary tonality is not necessarily clean. The standard technique
        involves inferring the modality from the triad built on the i-th tone of the base modality. However,
        the actual technique to be used can be a variable. The secondary_tonality argument is meant for cases where
        the standard technique does not hold up - and provides a means for specifying the exact secondary tonality
        when the standard technique does not apply.
        """
        Chord.__init__(self, secondary_chord_template, diatonic_tonality)

        # Build the tonality upon which the primary chord is based
        diatonic_basis = self.diatonic_tonality.get_tone(self.chord_template.secondary_scale_degree - 1)

        # if no secondary modality specified?
        #  Use diatonic_tonality + secondary scale degree.  Determine the triad type of the natural triad there, and
        #  if major, use major modality.  If minor, use melodic minor modality.  Otherwise flag an error.
        if not self.chord_template.secondary_modality:
            triad = TertianChordTemplate.get_triad(diatonic_tonality, self.chord_template.secondary_scale_degree)
            if triad:
                modality = ModalityType.Major if triad.chord_type.value == TertianChordType.Maj or \
                                                 triad.chord_type.value == TertianChordType.Aug else \
                           ModalityType.MelodicMinor if triad.chord_type.value == TertianChordType.Min or \
                                                 triad.chord_type.value == TertianChordType.Dim else None
                if modality is None:
                    raise Exception('Illegal secondary modality for secondary chord')
            else:
                raise Exception('Cannot determine secondary modality for secondary chord')
        else:
            modality = self.chord_template.secondary_modality

        self.__secondary_tonality = Tonality.create(modality, diatonic_basis) \
            if not secondary_tonality else secondary_tonality

        # Create the principal chord
        self.__primary_chord = self.chord_template.principal_chord_template.create_chord(self.secondary_tonality)

    @property
    def chord_type(self):
        return self.primary_chord.chord_type

    @property
    def root_tone(self):
        return self.primary_chord.root_tone

    @property
    def tones(self):
        return self.primary_chord.tones

    @property
    def primary_chord(self):
        return self.__primary_chord

    @property
    def secondary_tonality(self):
        return self.__secondary_tonality

    def __str__(self):
    #    from harmonicmodel.chord_template import ChordTemplate
        s = str(ChordTemplate.SCALE_DEGREE_REVERSE_MAP[self.chord_template.secondary_scale_degree])
        t = str(self.secondary_tonality.modality.modality_type)
        tones = ', '.join(str(tone[0].diatonic_symbol) for tone in self.primary_chord.tones)
        return '{0}/{1}({2}) [{3}]'.format(str(self.primary_chord.chord_template), s, t, tones)

# ==============================================================================
class TertianChordException(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)


class TertianChordType:
    """
    Enum class defining all the tertian chord varieties.
    """
    Maj6, Maj, Min6, Min, Dim, Aug, MajSus2, MajSus4, MajSus, Maj7, Maj7Sus4, Maj7Sus2, Maj7Sus, Min7, Dom7, Dom7Sus4, \
    Dom7Sus2, Dom7Sus, Dim7, HalfDim7, MinMaj7, AugMaj7, Aug7, DimMaj7, Dom7Flat5, Fr, Ger, It, N6 = range(29)

    def __init__(self, ctype):
        self.value = ctype

    def __str__(self):
        if self.value == TertianChordType.Maj:
            return 'Maj'
        if self.value == TertianChordType.Min:
            return 'Min'
        if self.value == TertianChordType.Dim:
            return 'Dim'
        if self.value == TertianChordType.Aug:
            return 'Aug'
        if self.value == TertianChordType.MajSus2:
            return 'MajSus2'
        if self.value == TertianChordType.MajSus4:
            return 'MajSus4'
        if self.value == TertianChordType.MajSus:
            return 'MajSus'
        if self.value == TertianChordType.Maj7:
            return 'Maj7'
        if self.value == TertianChordType.Maj7Sus4:
            return 'Maj7Sus4'
        if self.value == TertianChordType.Maj7Sus2:
            return 'Maj7Sus2'
        if self.value == TertianChordType.Maj7Sus:
            return 'Maj7Sus'
        if self.value == TertianChordType.Min7:
            return 'Min7'
        if self.value == TertianChordType.Dom7:
            return 'Dom7'
        if self.value == TertianChordType.Dom7Sus4:
            return 'Dom7Sus4'
        if self.value == TertianChordType.Dom7Sus2:
            return 'Dom7Sus2'
        if self.value == TertianChordType.Dom7Sus:
            return 'Dom7Sus'
        if self.value == TertianChordType.Dim7:
            return 'Dim7'
        if self.value == TertianChordType.HalfDim7:
            return 'HalfDim7'
        if self.value == TertianChordType.MinMaj7:
            return 'MinMaj7'
        if self.value == TertianChordType.AugMaj7:
            return 'AugMaj7'
        if self.value == TertianChordType.Aug7:
            return 'Aug7'
        if self.value == TertianChordType.DimMaj7:
            return 'DimMaj7'
        if self.value == TertianChordType.Dom7Flat5:
            return 'Dom7Flat5'
        if self.value == TertianChordType.Maj6:
            return 'Maj6'
        if self.value == TertianChordType.Min6:
            return 'Min6'
        if self.value == TertianChordType.Fr:
            return 'Fr'
        if self.value == TertianChordType.Ger:
            return 'Ger'
        if self.value == TertianChordType.It:
            return 'It'
        if self.value == TertianChordType.N6:
            return 'N6'

    @staticmethod
    def to_type(t_string):
        t = None
        if t_string == 'Maj':
            t = TertianChordType.Maj
        elif t_string == 'MajSus2':
            t = TertianChordType.MajSus2
        elif t_string == 'MajSus4':
            t = TertianChordType.MajSus4
        elif t_string == 'MajSus':
            t = TertianChordType.MajSus
        elif t_string == 'Min':
            t = TertianChordType.Min
        elif t_string == 'Dim':
            t = TertianChordType.Dim
        elif t_string == 'Aug':
            t = TertianChordType.Aug
        elif t_string == 'Maj7':
            t = TertianChordType.Maj7
        elif t_string == 'Maj7Sus2':
            t = TertianChordType.Maj7Sus2
        elif t_string == 'Maj7Sus4':
            t = TertianChordType.Maj7Sus4
        elif t_string == 'Maj7Sus':
            t = TertianChordType.Maj7Sus
        elif t_string == 'Min7':
            t = TertianChordType.Min7
        elif t_string == 'Dom7':
            t = TertianChordType.Dom7
        elif t_string == 'Dom7Sus2':
            t = TertianChordType.Dom7Sus2
        elif t_string == 'Dom7Sus4':
            t = TertianChordType.Dom7Sus4
        elif t_string == 'Dom7Sus':
            t = TertianChordType.Dom7Sus
        elif t_string == 'Dim7':
            t = TertianChordType.Dim7
        elif t_string == 'HalfDim7':
            t = TertianChordType.HalfDim7
        elif t_string == 'MinMaj7':
            t = TertianChordType.MinMaj7
        elif t_string == 'AugMaj7':
            t = TertianChordType.AugMaj7
        elif t_string == 'Aug7':
            t = TertianChordType.Aug7
        elif t_string == 'DimMaj7':
            t = TertianChordType.DimMaj7
        elif t_string == 'Dom7Flat5':
            t = TertianChordType.Dom7Flat5
        elif t_string == 'Maj6':
            t = TertianChordType.Maj6
        elif t_string == 'Min6':
            t = TertianChordType.Min6
        elif t_string == 'Fr':
            t = TertianChordType.Fr
        elif t_string == 'Ger':
            t = TertianChordType.Ger
        elif t_string == 'It':
            t = TertianChordType.It
        elif t_string == 'N6':
            t = TertianChordType.N6
        return TertianChordType(t) if t is not None else None

    def __eq__(self, y):
        return self.value == y.value

    def __hash__(self):
        return self.__str__().__hash__()


class TertianChordTemplate(ChordTemplate):
    """
    Template for tertian chords.  We have a regular expression syntax to cover these cases that roughly goes:

    (T|t)?((I|II|...)|A-G)(Maj|Min| ...)?(+?(b|#)?[2-15])*(@[1-7])?
    
    Examples:
      IIMaj7+b9@3
      CDom7
      TIVDim7Flat5#3      The third is sharped
      
    Note: The idea of modifiying scale degree ala:
              (+|-)?(I|II|...)
          was considered.  The notation traces back to -ii being used as a shorthand for Neopolian Six chords.
          The reference:
              https://en.wikipedia.org/wiki/Neapolitan_chord
          provides an interesting argument of using Phrygian scales to provide an underpinning for Neopolican.
          However, to take the notation to the next level, cases such as +iv and -vi need similar underpinning,
          which at this point cannot be found.  So we are not allowing this notation unless a solid theoretical
          solution appears.
    """

    TERTIAN_CHORD_TYPE_MAP = {
        TertianChordType.Maj: [IntervalN(1, IntervalType.Perfect),
                               IntervalN(3, IntervalType.Major),
                               IntervalN(5, IntervalType.Perfect)],
        TertianChordType.MajSus2: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(2, IntervalType.Major),
                                   IntervalN(5, IntervalType.Perfect)],
        TertianChordType.MajSus4: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(4, IntervalType.Perfect),
                                   IntervalN(5, IntervalType.Perfect)],
        TertianChordType.MajSus: [IntervalN(1, IntervalType.Perfect),
                                  IntervalN(4, IntervalType.Perfect),
                                  IntervalN(5, IntervalType.Perfect)],
        TertianChordType.Min: [IntervalN(1, IntervalType.Perfect),
                               IntervalN(3, IntervalType.Minor),
                               IntervalN(5, IntervalType.Perfect)],
        TertianChordType.Dim: [IntervalN(1, IntervalType.Perfect),
                               IntervalN(3, IntervalType.Minor),
                               IntervalN(5, IntervalType.Diminished)],
        TertianChordType.Aug: [IntervalN(1, IntervalType.Perfect),
                               IntervalN(3, IntervalType.Major),
                               IntervalN(5, IntervalType.Augmented)],
        TertianChordType.Maj7: [IntervalN(1, IntervalType.Perfect),
                                IntervalN(3, IntervalType.Major),
                                IntervalN(5, IntervalType.Perfect),
                                IntervalN(7, IntervalType.Major)],
        TertianChordType.Maj7Sus2: [IntervalN(1, IntervalType.Perfect),
                                    IntervalN(2, IntervalType.Major),
                                    IntervalN(5, IntervalType.Perfect),
                                    IntervalN(7, IntervalType.Major)],
        TertianChordType.Maj7Sus4: [IntervalN(1, IntervalType.Perfect),
                                    IntervalN(4, IntervalType.Perfect),
                                    IntervalN(5, IntervalType.Perfect),
                                    IntervalN(7, IntervalType.Major)],
        TertianChordType.Maj7Sus: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(4, IntervalType.Perfect),
                                   IntervalN(5, IntervalType.Perfect),
                                   IntervalN(7, IntervalType.Major)],
        TertianChordType.Min7: [IntervalN(1, IntervalType.Perfect),
                                IntervalN(3, IntervalType.Minor),
                                IntervalN(5, IntervalType.Perfect),
                                IntervalN(7, IntervalType.Minor)],
        TertianChordType.Dom7: [IntervalN(1, IntervalType.Perfect),
                                IntervalN(3, IntervalType.Major),
                                IntervalN(5, IntervalType.Perfect),
                                IntervalN(7, IntervalType.Minor)],
        TertianChordType.Dom7Sus2: [IntervalN(1, IntervalType.Perfect),
                                    IntervalN(2, IntervalType.Major),
                                    IntervalN(5, IntervalType.Perfect),
                                    IntervalN(7, IntervalType.Minor)],
        TertianChordType.Dom7Sus4: [IntervalN(1, IntervalType.Perfect),
                                    IntervalN(4, IntervalType.Perfect),
                                    IntervalN(5, IntervalType.Perfect),
                                    IntervalN(7, IntervalType.Minor)],
        TertianChordType.Dom7Sus: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(4, IntervalType.Perfect),
                                   IntervalN(5, IntervalType.Perfect),
                                   IntervalN(7, IntervalType.Minor)],
        TertianChordType.Dim7: [IntervalN(1, IntervalType.Perfect),
                                IntervalN(3, IntervalType.Minor),
                                IntervalN(5, IntervalType.Diminished),
                                IntervalN(7, IntervalType.Diminished)],
        TertianChordType.HalfDim7: [IntervalN(1, IntervalType.Perfect),
                                    IntervalN(3, IntervalType.Minor),
                                    IntervalN(5, IntervalType.Diminished),
                                    IntervalN(7, IntervalType.Minor)],
        TertianChordType.MinMaj7: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(3, IntervalType.Minor),
                                   IntervalN(5, IntervalType.Perfect),
                                   IntervalN(7, IntervalType.Major)],
        TertianChordType.AugMaj7: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(3, IntervalType.Major),
                                   IntervalN(5, IntervalType.Augmented),
                                   IntervalN(7, IntervalType.Major)],
        TertianChordType.Aug7: [IntervalN(1, IntervalType.Perfect),
                                IntervalN(3, IntervalType.Major),
                                IntervalN(5, IntervalType.Augmented),
                                IntervalN(7, IntervalType.Minor)],
        TertianChordType.DimMaj7: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(3, IntervalType.Minor),
                                   IntervalN(5, IntervalType.Diminished),
                                   IntervalN(7, IntervalType.Major)],
        TertianChordType.Dom7Flat5: [IntervalN(1, IntervalType.Perfect),
                                     IntervalN(3, IntervalType.Major),
                                     IntervalN(5, IntervalType.Diminished),
                                     IntervalN(7, IntervalType.Minor)],
        TertianChordType.Maj6: [IntervalN(1, IntervalType.Perfect),
                                IntervalN(3, IntervalType.Major),
                                IntervalN(5, IntervalType.Perfect),
                                IntervalN(6, IntervalType.Major)],
        TertianChordType.Min6: [IntervalN(1, IntervalType.Perfect),
                                IntervalN(3, IntervalType.Minor),
                                IntervalN(5, IntervalType.Perfect),
                                IntervalN(6, IntervalType.Major)],
        TertianChordType.Fr: [IntervalN(6, IntervalType.Augmented),
                              IntervalN(1, IntervalType.Perfect),
                              IntervalN(2, IntervalType.Major),
                              IntervalN(4, IntervalType.Augmented)],
        TertianChordType.Ger: [IntervalN(6, IntervalType.Augmented),
                               IntervalN(1, IntervalType.Perfect),
                               IntervalN(3, IntervalType.Minor),
                               IntervalN(4, IntervalType.Augmented)],
        TertianChordType.It: [IntervalN(6, IntervalType.Minor),
                              IntervalN(1, IntervalType.Perfect),
                              IntervalN(4, IntervalType.Augmented)],
        TertianChordType.N6: [IntervalN(6, IntervalType.Minor),
                              IntervalN(2, IntervalType.Minor),
                              IntervalN(4, IntervalType.Perfect)],
    }

    # Note that augmented 6th chords and the neopolitan have the sixth as the root.  This is the normal position.
    # And inversions specified alter that order.  So, root position would be inversion == 2.

    GROUP_BASIS = 'Basis'
    GROUP_BASIS_TAG = '?P<' + GROUP_BASIS + '>'
    P1_BASIS = '(' + GROUP_BASIS_TAG + 'T|t)?'

    SCALE_DEGREE = 'III|II|IV|VII|VI|V|I|iii|ii|iv|vii|vi|v|i'
    GROUP_SCALE_DEGREE = 'ScaleDegree'
    GROUP_SCALE_DEGREE_TAG = '?P<' + GROUP_SCALE_DEGREE + '>'

    GROUP_DIATONIC_TONE = 'DiatonicTone'
    GROUP_DIATONIC_TONE_NAME = '?P<' + GROUP_DIATONIC_TONE + '>'
    ROOT = '((' + GROUP_DIATONIC_TONE_NAME + DiatonicTone.DIATONIC_PATTERN_STRING + ')|' + \
           '(' + GROUP_SCALE_DEGREE_TAG + SCALE_DEGREE + '))'

    TENSION_RANGE = '(10|11|12|13|14|15|9|8|7|6|5|4|3|2|1)'
    TENSION = '((\\+)' + '(bb|b|##|#)?' + TENSION_RANGE + ')'
    GROUP_TENSIONS = 'Tensions'
    GROUP_TENSIONS_TAG = '?P<' + GROUP_TENSIONS + '>'
    TERTIAN_TENSIONS = '(' + GROUP_TENSIONS_TAG + TENSION + '*)'

    CHORD_NAMES = 'Maj7Sus4|Maj7Sus2|Maj7Sus|Maj7|MajSus4|MajSus2|MajSus|Maj6|Maj|Min7|MinMaj7|Min6|Min|DimMaj7|' \
                  'Dom7Flat5|Dim7|Dim|AugMaj7|Aug7|Aug|Dom7Sus4|Dom7Sus2|Dom7Sus|Dom7|HalfDim7|Fr|Ger|It|N6'

    GROUP_CHORD = 'Chord'
    GROUP_CHORD_TAG = '?P<' + GROUP_CHORD + '>'
    CHORDS = '(' + GROUP_CHORD_TAG + CHORD_NAMES + ')?'

    INVERSION = '[1-7]'
    GROUP_INVERSION = 'Inversion'
    GROUP_INVERSION_TAG = '?P<' + GROUP_INVERSION + '>'
    # INVERSIONS = '(\@(' + GROUP_INVERSION_TAG + INVERSION + '))?'

    INVERSION_TENSION = 'InvTension'
    INVERSION_TENSION_TAG = '?P<' + INVERSION_TENSION + '>'
    INVERSION_TENSION_STRUCT = '\\(' + '(bb|b|##|#)?' + TENSION_RANGE + '\\)'
    INVERSION_TENSION_PATTERN = '(' + INVERSION_TENSION_TAG + INVERSION_TENSION_STRUCT + ')'
    INVERSIONS = '(\\@(' + GROUP_INVERSION_TAG + INVERSION + '|' + INVERSION_TENSION_PATTERN + '))?'

    # full parse string and accompanying pattern for the tertian chord grammar.
    TERTIAN_PARSE_STRING = P1_BASIS + ROOT + CHORDS + TERTIAN_TENSIONS + INVERSIONS + '$'
    TERTIAN_PATTERN = re.compile(TERTIAN_PARSE_STRING)

    TENSION_PATTERN = re.compile(TENSION)
    INVERSE_TENSION_PATTERN = re.compile(INVERSION_TENSION_STRUCT)

    def __init__(self, diatonic_basis, scale_degree, chord_type, tension_intervals, inversion, inversion_interval=None):
        """
        Constructor
        
        Args:
          diatonic_basis: DiatonicTone used as root of chord, e.g. C major chord, the C part
          scale_degree: int version of roman numeral
          chord_type: The chord type ala TertianChordType
          tension_intervals: list of IntervalN's comprising the tensions
          inversion: int for which of the chord tones (ordinal) serves as root [origin 1]
          inversion_interval: if specified, indicates which interval should be the base.
          (both this in interval cannot be non-null.)
        """
        ChordTemplate.__init__(self)
        self.__diatonic_basis = diatonic_basis  # DiatonicTone

        self.__scale_degree = scale_degree

        self.__chord_type = chord_type
        self.__tension_intervals = tension_intervals  # list of [number, augmentation] representing intervals
        self.__inversion = inversion  # which tone of n is the bass
        self.__inversion_interval = inversion_interval

        self.__base_intervals = []
        if chord_type:
            self.__base_intervals.extend(TertianChordTemplate.TERTIAN_CHORD_TYPE_MAP[self.chord_type.value])

        # Remove duplicate tensions
        seen = set()
        seen_add = seen.add
        deduped_tension_intervals = [tension for tension in self.tension_intervals
                                     if not (tension.semitones() in seen or seen_add(tension.semitones()))]
        self.__tension_intervals = deduped_tension_intervals

        # Inversion check - only if chord type was given, not for cases like II
        if self.chord_type and (self.inversion is not None) and \
                self.inversion > len(self.base_intervals) + len(self.tension_intervals):
            raise Exception('Illegal inversion {0} for {1}'.format(self.inversion, self.__str__()))

        if self.inversion_interval is not None and \
                self.inversion_interval not in self.base_intervals and \
                self.inversion_interval not in self.tension_intervals:
            raise Exception('Illegal inversion_interval {0}'.format(self.inversion_interval))

    @property
    def diatonic_basis(self):
        return self.__diatonic_basis

    @property
    def scale_degree(self):
        return self.__scale_degree

    @property
    def chord_type(self):
        return self.__chord_type

    @property
    def base_intervals(self):
        return self.__base_intervals

    @property
    def tension_intervals(self):
        return self.__tension_intervals

    @property
    def inversion(self):
        return self.__inversion

    @property
    def inversion_interval(self):
        return self.__inversion_interval

    @staticmethod
    def get_chord_type(interval_list):
        for k, v in list(TertianChordTemplate.TERTIAN_CHORD_TYPE_MAP.items()):
            if len(interval_list) == len(v):
                same = True
                for i in range(0, len(v)):
                    if not interval_list[i].is_same(v[i]):
                        same = False
                        break
                if same:
                    return TertianChordType(k)
        return None

    @staticmethod
    def get_triad(diatonic_tonality, scale_degree):
        return TertianChordTemplate.parse('t{0}'.format(
            ChordTemplate.SCALE_DEGREE_REVERSE_MAP[scale_degree])).create_chord(diatonic_tonality)

    def create_chord(self, diatonic_tonality=None):
        return TertianChord(self, diatonic_tonality)

    def __str__(self):
        inv = ''
        if self.inversion is not None and self.inversion != 1:
            inv = '@' + str(self.inversion)
        elif self.inversion_interval is not None:
            inv = '@(' + str(self.inversion_interval) + ')'
        return 'T{0}{1}{2}{3}'.format(
            self.diatonic_basis.diatonic_symbol if self.diatonic_basis else
            (str(ChordTemplate.SCALE_DEGREE_REVERSE_MAP[self.scale_degree])),
            self.chord_type if self.chord_type else '',
            ' '.join(str(w) for w in self.tension_intervals),
            inv)

    @staticmethod
    def parse(chord_string):
        """
        Parse an input string into a TertialChordTemplate.
        
        Args:
          chord_string: string input representing chord
        Returns:
          TertianChordTemplate       
        """
        if not chord_string:
            raise TertianChordException('Unable to parse chord string to completion: {0}'.format(chord_string))
        m = TertianChordTemplate.TERTIAN_PATTERN.match(chord_string)
        if not m:
            raise TertianChordException('Unable to parse chord string to completion: {0}'.format(chord_string))

        scale_degree = m.group(TertianChordTemplate.GROUP_SCALE_DEGREE)
        if scale_degree:
            scale_degree = ChordTemplate.SCALE_DEGREE_MAP[scale_degree]
        if m.group(TertianChordTemplate.GROUP_DIATONIC_TONE) is not None:
            diatonic_basis = DiatonicTone(m.group(TertianChordTemplate.GROUP_DIATONIC_TONE))
        else:
            diatonic_basis = None
        chord_name = m.group(TertianChordTemplate.GROUP_CHORD)
        chord_type = None
        if chord_name:
            chord_type = TertianChordType.to_type(chord_name)
        inversion_text = m.group(TertianChordTemplate.GROUP_INVERSION)
        inversion_tension = m.group(TertianChordTemplate.INVERSION_TENSION)
        inversion_interval = None
        inversion = None
        if inversion_tension:
            tensions_parse = TertianChordTemplate.INVERSE_TENSION_PATTERN.findall(inversion_tension)
            for tension in tensions_parse:  # should only be 1
                aug = DiatonicTone.AUGMENTATION_OFFSET_MAPPING[tension[0]]
                interval_type = IntervalN.available_types(int(tension[1]))[aug]
                inversion_interval = IntervalN(int(tension[1]), interval_type)
                logging.info('inversion_interval = {0}'.format(str(inversion_interval)))
        elif inversion_text:
            inversion = int(inversion_text)
        else:
            inversion = 1

        tensions = []
        if m.group(TertianChordTemplate.GROUP_TENSIONS):
            tensions_parse = TertianChordTemplate.TENSION_PATTERN.findall(m.group(TertianChordTemplate.GROUP_TENSIONS))
            for tension in tensions_parse:
                aug = DiatonicTone.AUGMENTATION_OFFSET_MAPPING[tension[2]]
                if aug not in IntervalN.available_types(int(tension[3])):
                    raise TertianChordException('Invalid interval specification for tension \'{0}\''.format(tension[0]))
                interval_type = IntervalN.available_types(int(tension[3]))[aug]
                interval = IntervalN(int(tension[3]), interval_type)
                tensions.append(interval)

        return TertianChordTemplate(diatonic_basis, scale_degree, chord_type, tensions, inversion, inversion_interval)

# ==============================================================================
class TertianChord(Chord):
    """
    Class that defines a tertian chord
    This class create it tones based on differing specifications found in TertianChordTemplate:
    1) If root is given by a diatonic tone (and chord type), the diatonic tonality is not used,
       and strict interval specs decide the other notes.
    2) If root is given by diatonic tonality and scale reference, 
       a) If the chord type is given, the tones are built as in 1) but with the root determined by
          scale degree on tonality.
       b) If the chord type is note given, the tones are built on the tonality itself.  The chord type determined by
          the tones.
       
    Inversion results in a re-ordering of the tone, making the inversion tone the first tone.
    
    The result self.tones is a list of duplets (diatonic_tone, interval)
    """

    def __init__(self, tertian_chord_template, diatonic_tonality=None):
        """
        Constructor.
        Args:
          tertian_chord_template: TertianChordTemplate
          diatonic_tonality: DiatonicTonality (used in scale degree chord formation)
        """
        Chord.__init__(self, tertian_chord_template, diatonic_tonality)    
        
        self.__tones = []
        self.__chord_type = self.chord_template.chord_type
        
        self.__root_tone = self.chord_template.diatonic_basis
        
        if self.chord_template.diatonic_basis:
            if self.chord_type:
                self.__create_chord_on_diatonic(self.root_tone)
            else:
                self.__create_chord_on_diatonic_without_type(self.root_tone)
        else:
            if not self.diatonic_tonality:
                raise Exception(
                    'Diatonic tonality must be specified for chords based on scale degree: {0}'.
                    format(str(self.chord_template)))
            if self.chord_type:
                self.__create_chord_on_scale_degree_with_chord_type()
            else:
                self.__create_chord_on_scale_degree()
            
    def __create_chord_on_diatonic(self, diatonic_tone):
        self.chord_basis = []
        for interval in self.chord_template.base_intervals:
            tone = interval.get_end_tone(diatonic_tone)
            self.__tones.append((tone, interval))
            self.chord_basis.append(interval)
          
        for interval in self.chord_template.tension_intervals:
            tone = interval.get_end_tone(diatonic_tone)   
            self.__tones.append((tone, interval))
            
        self.__set_inversion()

    def __create_chord_on_diatonic_without_type(self, diatonic_tone):
    #    from tonalmodel.tonality import Tonality
    #    from tonalmodel.modality import ModalityType
    #    from harmonicmodel.tertian_chord_template import TertianChordTemplate
        diatonic_tonality = Tonality.create(ModalityType.Major, diatonic_tone)
        tone_scale = diatonic_tonality.annotation

        self.chord_basis = []
        base_tone = None
        for i in range(0, 3):
            tone = tone_scale[(2 * i) % (len(tone_scale) - 1)]
            if i == 0:
                base_tone = tone

            pitch_a = DiatonicPitch(1, diatonic_tone)
            b_octave = 2 if base_tone.diatonic_index > tone.diatonic_index else 1
            pitch_b = DiatonicPitch(b_octave, tone.diatonic_symbol)
            interval = IntervalN.create_interval(pitch_a, pitch_b)
            self.chord_basis.append(interval)

            self.__tones.append((tone, interval))
        self.__set_inversion()

        self.__chord_type = TertianChordTemplate.get_chord_type(self.chord_basis)

    def __create_chord_on_scale_degree(self):
    #    from harmonicmodel.tertian_chord_template import TertianChordTemplate
        root_index = self.chord_template.scale_degree - 1
        tone_scale = self.diatonic_tonality.annotation
        
        self.chord_basis = []
        base_tone = None
        for i in range(0, 3):
            tone = tone_scale[(root_index + 2 * i) % (len(tone_scale) - 1)]
            if i == 0:
                base_tone = tone
                       
            pitch_a = DiatonicPitch(1, tone_scale[root_index].diatonic_symbol)
            b_octave = 2 if base_tone.diatonic_index > tone.diatonic_index else 1
            pitch_b = DiatonicPitch(b_octave, tone.diatonic_symbol)
            interval = IntervalN.create_interval(pitch_a, pitch_b)
            self.chord_basis.append(interval)
            
            self.__tones.append((tone, interval))
        self.__set_inversion()
        
        self.__chord_type = TertianChordTemplate.get_chord_type(self.chord_basis)    
        
    def __create_chord_on_scale_degree_with_chord_type(self):
        root_index = self.chord_template.scale_degree - 1
        tone_scale = self.diatonic_tonality.annotation
        self.__root_tone = tone_scale[root_index]
        
        self.__create_chord_on_diatonic(self.__root_tone)
        
    def __set_inversion(self):
        invert_id = -1
        if self.chord_template.inversion:
            if self.chord_template.inversion == 1:
                return
            invert_id = self.chord_template.inversion
        elif self.chord_template.inversion_interval:
            # find the interval

            for i in range(0, len(self.chord_basis)):
                if self.chord_basis[i].is_same(self.chord_template.inversion_interval):
                    invert_id = i + 1
                    break
            if invert_id == -1 and self.chord_template.tension_intervals:
                for i in range(0, len(self.chord_template.tension_intervals)):
                    if self.chord_template.tension_intervals[i] == self.chord_template.inversion_interval:
                        invert_id = i + 1 + len(self.chord_basis)
                        break
            if invert_id == -1:
                raise Exception(
                    "Could not find interval {0} for chord off template {1}".
                    format(self.chord_template.inversion_interval, self.chord_template))
            # remove the cited index
        item = self.__tones[invert_id - 1]
        self.__tones.remove(item)
        self.__tones.insert(0, item)
    
    @property        
    def tones(self):
        new_list = []
        new_list.extend(self.__tones)
        return new_list
    
    @property
    def chord_type(self):
        return self.__chord_type
    
    @property
    def root_tone(self):
        return self.__root_tone
    
    def sorted_tones(self):
        return sorted(self.tones, key=lambda tone: tone[1].semitones())
    
    def __str__(self):
        return '{0} [{1}]'.format(str(self.chord_template),
                                  ', '.join(str(tone[0].diatonic_symbol) for tone in self.tones))

# ==============================================================================
class SecundalChord(Chord):
    """
    Class that defines a secundal chord
    This class create it tones based on differing specifications found in SecundalChordTemplate:
    1) If root is given by a diatonic tone (and chord type), the diatonic tonality is not used, and strict interval
       specs decide the other notes.
    2) If root is given by diatonic tonality and scale reference, 
       a) If the chord type is given, the tones are built as in 1) but with the root determined by scale degree on
          tonality.
       b) If the chord type is note given, the tones are built on the tonality itself.  The chord type determined by
          the tones.
       
    Inversion results in a re-ordering of the tone, making the inversion tone the first tone.
    
    The result self.tones is a list of duplets (diatonic_tone, interval)
    """

    def __init__(self, secundal_chord_template, diatonic_tonality=None):
        """
        Constructor.
        Args:
          secundal_chord_template: SecundalChordTemplate
          diatonic_tonality: DiatonicTonality (used in scale degree chord formation)
        """
    #    from harmonicmodel.secundal_chord_template import SecundalChordTemplate
        Chord.__init__(self, secundal_chord_template, diatonic_tonality) 
        
        self.__tones = []
        self.__chord_type = self.chord_template.chord_type
        
        self.__root_tone = self.chord_template.diatonic_basis
        
        if self.__root_tone:
            if len(self.chord_template.base_intervals) != 0:
                self.__create_chord_on_diatonic(self.root_tone)
            else:
                if self.diatonic_tonality is None:
                    self.__create_chord_on_root_no_base_intervals(self.root_tone)
                else:
                    self.__create_chord_on_diatonic_tonality(self.root_tone, self.diatonic_tonality)
        else:
            if not self.diatonic_tonality:
                raise Exception(
                    'Diatonic tonality must be specified for chords based on scale degree: {0}'.
                    format(str(self.chord_template)))
            if self.chord_template.base_intervals:
                self.__create_chord_on_scale_degree_with_chord_type()
            else:
                self.__create_chord_on_scale_degree() 
        
        self.__set_inversion() 
        self.__chord_type = SecundalChordTemplate.get_chord_type(self.chord_basis)  
                
    @property
    def chord_type(self):
        return self.__chord_type
    
    @property
    def root_tone(self):
        return self.__root_tone
    
    @property
    def tones(self):
        new_list = []
        new_list.extend(self.__tones)
        return new_list 
                
    def __create_chord_on_diatonic(self, diatonic_tone):
        self.chord_basis = []
        current_tone = diatonic_tone
        for interval in self.chord_template.base_intervals:               
            tone = interval.get_end_tone(current_tone)
            self.__tones.append((tone, interval))
            self.chord_basis.append(interval)
            current_tone = tone

    def __create_chord_on_root_no_base_intervals(self, diatonic_tone):
        # Assume MM or MajMaj
        self.chord_basis = []
        current_tone = diatonic_tone
        intervals = [IntervalN(1, IntervalType.Perfect),
                     IntervalN(2, IntervalType.Major),
                     IntervalN(2, IntervalType.Major)]
        for i in range(0, 3):
            tone = intervals[i].get_end_tone(current_tone)
            self.__tones.append((tone, intervals[i]))
            self.chord_basis.append(intervals[i])
            current_tone = tone
                    
    def __create_chord_on_diatonic_tonality(self, diatonic_tone, diatonic_tonality):
        if not diatonic_tonality:
            raise Exception("Cannot base secundal chord on tone {0} without tonality.".format(
                diatonic_tone.diatonic_symbol))
        # The tonality must include this tone.
        tone_scale = diatonic_tonality.annotation
        found_index = -1
        for i in range(0, len(tone_scale)):
            if diatonic_tone == tone_scale[i]:
                found_index = i
                break
        if found_index == -1:
            raise Exception("For secundal chord based on tone {0}, tone must be in given tonality {1}".format(
                diatonic_tone.diatonic_symbol, diatonic_tonality))
        self.chord_basis = []
        basis_tone = tone_scale[found_index]
        for i in range(0, 3):               
            tone = tone_scale[(found_index + i) % (len(tone_scale) - 1)]
            pitch_a = DiatonicPitch(1, basis_tone.diatonic_symbol)
            b_octave = 2 if basis_tone.diatonic_index > tone.diatonic_index else 1
            pitch_b = DiatonicPitch(b_octave, tone.diatonic_symbol)
            interval = IntervalN.create_interval(pitch_a, pitch_b)
            # If for any reason, the interval is not perfect or augmented (we know it is a 4th), just adjust tone upward
            #    It is unknown if this can happen in a diatonic scale in practice.
            if interval.interval_type.value == IntervalType.Diminished:
                tone = DiatonicTone.alter_tone_by_augmentation(tone, 1)
                pitch_b = DiatonicPitch(b_octave, tone.diatonic_symbol)
                interval = IntervalN.create_interval(pitch_a, pitch_b)
            self.chord_basis.append(interval)
            
            self.__tones.append((tone, interval))
            basis_tone = tone 
        
    def __create_chord_on_scale_degree(self):
        root_index = self.chord_template.scale_degree - 1
        tone_scale = self.diatonic_tonality.annotation
        
        basis_tone = tone_scale[root_index]

        self.__create_chord_on_root_no_base_intervals(basis_tone)
        
    def __create_chord_on_scale_degree_with_chord_type(self):
        root_index = self.chord_template.scale_degree - 1
        tone_scale = self.diatonic_tonality.annotation
        self.__root_tone = tone_scale[root_index]
        
        self.__create_chord_on_diatonic(self.__root_tone)
        
    def __set_inversion(self):
        invert_id = -1
        if self.chord_template.inversion:
            if self.chord_template.inversion == 1:
                return
            invert_id = self.chord_template.inversion
        # remove the cited index
        item = self.__tones[invert_id - 1]
        self.__tones.remove(item)
        self.__tones.insert(0, item)    
        
    def __str__(self):
        return '{0} [{1}]'.format(str(self.chord_template), ', '.join(
            str(tone[0].diatonic_symbol) for tone in self.tones))

# ==============================================================================
class SecundalChordException(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)


class SecundalChordType:
    """
    Enum class defining some significant secundal chord varieties.  There are 4 cases
    1) MinMin - Minor/Minor
    2) MajMin - Major/Minor
    3) MinMaj - Minor/Major
    4) MajMaj - Major/Major
    """
    MinMin, MajMin, MinMaj, MajMaj = range(4)
    
    def __init__(self, ctype):
        self.value = ctype
        
    def __str__(self):
        if self.value == SecundalChordType.MinMin:
            return 'MinMin'
        if self.value == SecundalChordType.MajMin:
            return 'MajMin'
        if self.value == SecundalChordType.MinMaj:
            return 'MinMaj'
        if self.value == SecundalChordType.MajMaj:
            return 'MajMaj'
        
    @staticmethod
    def to_type(t_string):
        t = None
        if t_string == 'MinMin':
            t = SecundalChordType.MinMin
        if t_string == 'MajMin':
            t = SecundalChordType.MajMin
        if t_string == 'MinMaj':
            t = SecundalChordType.MinMaj
        if t_string == 'MajMaj':
            t = SecundalChordType.MajMaj
        return SecundalChordType(t) if t is not None else None
        
    def __eq__(self, y):
        return self.value == y.value
    
    def __hash__(self):
        return self.__str__().__hash__()
    

class SecundalChordTemplate(ChordTemplate):
    """
    Template for secundal chords.  Secundal chords are based on incremental intervals of major and minor 2nd intervals.  
    
    We have a regular expression syntax to cover these cases that roughly goes:

    (S|s)((I|II|...)|A-G)((MinMin|MinMaj|MajMin|MajMaj| ...)|(m|M)+))?(@([1-9]([0-9]*)))?
    
    Examples:
      sII
      sCMmM
      
    Note: Along the lines of tertian, the idea of modifiying scale degree ala:
              (+|-)?(I|II|...)
          was considered.  The notation traces back to -ii being used as a shorthand for Neopolian Six chords.
          The reference:
              https://en.wikipedia.org/wiki/Neapolitan_chord
          provides an interesting argument of using Phrygian scales to provide an underpinning for Neopolican.
          However, to take the notation to the next level, cases such as +iv and -vi need similar underpinning,
          which at this point cannot be found.  So we are not allowing this notation unless a solid theoretical
          solution appears.
          
    """
    
    SECUNDAL_CHORD_TYPE_MAP = {
        SecundalChordType.MinMin: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(2, IntervalType.Minor),
                                   IntervalN(2, IntervalType.Minor)],
        SecundalChordType.MajMin: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(2, IntervalType.Major),
                                   IntervalN(2, IntervalType.Minor)],
        SecundalChordType.MinMaj: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(2, IntervalType.Minor),
                                   IntervalN(2, IntervalType.Major)],
        SecundalChordType.MajMaj: [IntervalN(1, IntervalType.Perfect),
                                   IntervalN(2, IntervalType.Major),
                                   IntervalN(2, IntervalType.Major)],
    }

    GROUP_BASIS = 'Basis'
    GROUP_BASIS_TAG = '?P<' + GROUP_BASIS + '>'
    P1_BASIS = '(' + GROUP_BASIS_TAG + 'S|s)?'
    
    SCALE_DEGREE = 'III|II|IV|VII|VI|V|I|iii|ii|iv|vii|vi|v|i'
    GROUP_SCALE_DEGREE = 'ScaleDegree'
    GROUP_SCALE_DEGREE_TAG = '?P<' + GROUP_SCALE_DEGREE + '>'    
    
    GROUP_DIATONIC_TONE = 'DiatonicTone'
    GROUP_DIATONIC_TONE_NAME = '?P<' + GROUP_DIATONIC_TONE + '>' 
    ROOT = '((' + GROUP_DIATONIC_TONE_NAME + DiatonicTone.DIATONIC_PATTERN_STRING + ')|' + \
           '(' + GROUP_SCALE_DEGREE_TAG + SCALE_DEGREE + '))'

    CHORD_NAMES = 'MinMin|MinMaj|MajMin|MajMaj'
    GROUP_CHORD = 'Chord'
    GROUP_CHORD_TAG = '?P<' + GROUP_CHORD + '>'  
    
    SECONDS = 'Seconds'
    SECONDS_SPECIFICATION_TAG = '?P<' + SECONDS + '>' 
    CHORDS = '((' + GROUP_CHORD_TAG + CHORD_NAMES + ')|(' + SECONDS_SPECIFICATION_TAG + '(m|M)+))?'
    
    INVERSION = '[1-9]([0-9]*)'
    GROUP_INVERSION = 'Inversion'
    GROUP_INVERSION_TAG = '?P<' + GROUP_INVERSION + '>'
    INVERSIONS = '(\\@(' + GROUP_INVERSION_TAG + INVERSION + '))?'
    
    # full parse string and accompanying pattern for the secundal chord grammar.
    SECUNDAL_PARSE_STRING = P1_BASIS + ROOT + CHORDS + INVERSIONS + '$'
    SECUNDAL_PATTERN = re.compile(SECUNDAL_PARSE_STRING)  

    def __init__(self, diatonic_basis, scale_degree, chord_type, specified_seconds, inversion):
        """
        Constructor
        
        Args:
          diatonic_basis: DiatonicTone used as root of chord, e.g. C major chord, the C part
          scale_degree: int version of roman numeral
          chord_type: The chord type ala SecundalChordType
          specified_seconds: list of IntervalN's secondary notes
          inversion: int for which of the chord tones (ordinal) serves as root [origin 1]
        """
        ChordTemplate.__init__(self)
        self.__diatonic_basis = diatonic_basis   # DiatonicTone
        
        self.__scale_degree = scale_degree   
        
        self.__chord_type = chord_type  
        self.__inversion = inversion    # which tone of n is the bass
        
        self.__base_intervals = list()
        if chord_type:
            self.__base_intervals.extend(SecundalChordTemplate.SECUNDAL_CHORD_TYPE_MAP[chord_type.value])
        self.__specified_seconds = specified_seconds
        if specified_seconds:
            intervals = list()
            intervals.append(IntervalN(1, IntervalType.Perfect))
            for ltr in specified_seconds:
                intervals.append(IntervalN(2, IntervalType.Major if ltr == 'M' else IntervalType.Minor))
            self.__base_intervals.extend(intervals)
                 
        # Inversion check - only if chord type was given, not for cases like II
        if self.chord_type and self.inversion > len(self.base_intervals):
            raise Exception('Illegal inversion {0} for {1}'.format(self.inversion, self.__str__()))
        
    @property
    def diatonic_basis(self):
        return self.__diatonic_basis
     
    @property   
    def scale_degree(self):
        return self.__scale_degree
    
    @property
    def chord_type(self):
        return self.__chord_type
    
    @property
    def base_intervals(self):
        return self.__base_intervals
    
    @property
    def inversion(self):
        return self.__inversion
    
    @property
    def specified_seconds(self):
        return self.__specified_seconds
        
    def create_chord(self, diatonic_tonality=None):
        return SecundalChord(self, diatonic_tonality) 
    
    @staticmethod
    def get_chord_type(interval_list):
        for k, v in list(SecundalChordTemplate.SECUNDAL_CHORD_TYPE_MAP.items()):
            if len(interval_list) == len(v):
                same = True
                for i in range(0, len(v)):
                    if not interval_list[i].is_same(v[i]):
                        same = False
                        break
                if same:
                    return SecundalChordType(k)
                
        # Build a M/m string
        t = ''
        for interval in interval_list[1:]:
            if interval.interval_type == IntervalType.Major:
                t += 'M'
            elif interval.interval_type == IntervalType.Minor:
                t += 'm'
            else:
                raise Exception('Illegal interval type for secundal {0}'.format(interval))
        return t
        
    def __str__(self):
        return 'S{0}{1}{2}{3}'.format(
            self.diatonic_basis.diatonic_symbol if self.diatonic_basis else
            (str(ChordTemplate.SCALE_DEGREE_REVERSE_MAP[self.scale_degree])),
            self.chord_type if self.chord_type else (self.specified_seconds if self.specified_seconds else ''),
            '@' + str(self.inversion) if self.inversion != 1 else '',
            ' --> ' + (' '.join(str(w) for w in self.base_intervals)),)
        
    @staticmethod   
    def parse(chord_string):
        """
        Parse an input string into a SecundalChordTemplate.
        
        Args:
          chord_string: string input representing chord
        Returns:
          SecundalChordTemplate       
        """
        if not chord_string:
            raise SecundalChordException('Unable to parse chord string to completion: {0}'.format(chord_string))
        m = SecundalChordTemplate.SECUNDAL_PATTERN.match(chord_string)
        if not m:
            raise SecundalChordException('Unable to parse chord string to completion: {0}'.format(chord_string))
        
        scale_degree = m.group(SecundalChordTemplate.GROUP_SCALE_DEGREE)
        if scale_degree:
            scale_degree = ChordTemplate.SCALE_DEGREE_MAP[scale_degree]
        if m.group(SecundalChordTemplate.GROUP_DIATONIC_TONE) is not None:
            diatonic_basis = DiatonicTone(m.group(SecundalChordTemplate.GROUP_DIATONIC_TONE))
        else:
            diatonic_basis = None
        chord_name = m.group(SecundalChordTemplate.GROUP_CHORD)
        chord_type = None
        if chord_name:
            chord_type = SecundalChordType.to_type(chord_name)
      
        seconds = m.group(SecundalChordTemplate.SECONDS) 
        inversion_text = m.group(SecundalChordTemplate.GROUP_INVERSION)
        inversion = int(inversion_text) if inversion_text else 1
        
        logging.info('{0}, {1}, {2}, {3}'.format(diatonic_basis if scale_degree is None else str(scale_degree),
                                                 str(chord_type) if chord_type else '',
                                                 seconds if seconds else '',
                                                 inversion))
        return SecundalChordTemplate(diatonic_basis, scale_degree, chord_type, seconds, inversion)

# ==============================================================================
class QuartalChord(Chord):
    """
    Class to represent an instance of a quartal chord.
    """

    def __init__(self, quartal_chord_template, diatonic_tonality=None):
        """
        Constructor.
        Args:
          quartal_chord_template: SecundalChordTemplate
          diatonic_tonality: DiatonicTonality (used in scale degree chord formation)
        """
        #from harmonicmodel.quartal_chord_template import QuartalChordTemplate
        Chord.__init__(self, quartal_chord_template, diatonic_tonality) 
        
        self.__tones = []
        self.__chord_type = self.chord_template.chord_type
        
        self.__root_tone = self.chord_template.diatonic_basis 
        
        if self.__root_tone:
            if len(self.chord_template.base_intervals) != 0:
                self.__create_chord_on_diatonic(self.root_tone)
            else:
                if self.diatonic_tonality is None:
                    self.__create_chord_on_root_no_base_intervals(self.root_tone)
                else:
                    self.__create_chord_on_diatonic_tonality(self.root_tone, self.diatonic_tonality)
        else:
            if not self.diatonic_tonality:
                raise Exception('Diatonic tonality must be specified for chords based on scale degree: {0}'.
                                format(str(self.chord_template)))
            if self.chord_template.base_intervals:
                self.__create_chord_on_scale_degree_with_chord_type()
            else:
                self.__create_chord_on_scale_degree() 
        
        self.__set_inversion() 
        self.__chord_type = QuartalChordTemplate.get_chord_type(self.chord_basis)
        
    @property
    def chord_type(self):
        return self.__chord_type
    
    @property
    def root_tone(self):
        return self.__root_tone
    
    @property
    def tones(self):
        new_list = []
        new_list.extend(self.__tones)
        return new_list 
    
    def __create_chord_on_diatonic(self, diatonic_tone):
        self.chord_basis = []
        current_tone = diatonic_tone
        for interval in self.chord_template.base_intervals:               
            tone = interval.get_end_tone(current_tone)
            self.__tones.append((tone, interval))
            self.chord_basis.append(interval)
            current_tone = tone

    def __create_chord_on_root_no_base_intervals(self, diatonic_tone):
        # Assume MM or MajMaj
        self.chord_basis = []
        current_tone = diatonic_tone
        intervals = [IntervalN(1, IntervalType.Perfect),
                     IntervalN(4, IntervalType.Perfect),
                     IntervalN(4, IntervalType.Perfect)]
        for i in range(0, 3):
            tone = intervals[i].get_end_tone(current_tone)
            self.__tones.append((tone, intervals[i]))
            self.chord_basis.append(intervals[i])
            current_tone = tone
                    
    def __create_chord_on_diatonic_tonality(self, diatonic_tone, diatonic_tonality):
        if not diatonic_tonality:
            raise Exception("Cannot base quartal chord on tone {0} without tonality.".
                            format(diatonic_tone.diatonic_symbol))
        # The tonality must include this tone.
        tone_scale = diatonic_tonality.annotation
        found_index = -1
        for i in range(0, len(tone_scale)):
            if diatonic_tone == tone_scale[i]:
                found_index = i
                break
        if found_index == -1:
            raise Exception("For quartal chord based on tone {0}, tone must be in given tonality {1}".
                            format(diatonic_tone.diatonic_symbol, diatonic_tonality))
        self.chord_basis = []
        basis_tone = tone_scale[found_index]
        for i in range(0, 3):               
            tone = tone_scale[(found_index + 3 * i) % (len(tone_scale) - 1)]
            pitch_a = DiatonicPitch(1, basis_tone.diatonic_symbol)
            b_octave = 2 if basis_tone.diatonic_index > tone.diatonic_index else 1
            pitch_b = DiatonicPitch(b_octave, tone.diatonic_symbol)
            interval = IntervalN.create_interval(pitch_a, pitch_b)
            self.chord_basis.append(interval)
            
            self.__tones.append((tone, interval))
            basis_tone = tone 
        
    def __create_chord_on_scale_degree(self):
        root_index = self.chord_template.scale_degree - 1
        tone_scale = self.diatonic_tonality.annotation
        
        basis_tone = tone_scale[root_index]

        self.__create_chord_on_root_no_base_intervals(basis_tone)
        
    def __create_chord_on_scale_degree_with_chord_type(self):
        root_index = self.chord_template.scale_degree - 1
        tone_scale = self.diatonic_tonality.annotation
        self.__root_tone = tone_scale[root_index]
        
        self.__create_chord_on_diatonic(self.__root_tone)
    
    def __set_inversion(self):
        invert_id = -1
        if self.chord_template.inversion:
            if self.chord_template.inversion == 1:
                return
            invert_id = self.chord_template.inversion
        # remove the cited index
        item = self.__tones[invert_id - 1]
        self.__tones.remove(item)
        self.__tones.insert(0, item)   
        
    def __str__(self):
        return '{0} [{1}]'.format(str(self.chord_template),
                                  ', '.join(str(tone[0].diatonic_symbol) for tone in self.tones))

# ==============================================================================
class QuartalChordException(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)


class QuartalChordType:
    """
    Enum class defining some significant quartal chord varieties.  There are 3 cases
    1) PerPer - Minor/Minor
    2) PerAug - Major/Minor
    3) AugPer - Minor/Major
    
    AugAug is not used as this amounts to root duplication.
    """
    PerPer, PerAug, AugPer = range(3)
    
    def __init__(self, ctype):
        self.value = ctype
        
    def __str__(self):
        if self.value == QuartalChordType.PerPer:
            return 'PerPer'
        if self.value == QuartalChordType.PerAug:
            return 'PerAug'
        if self.value == QuartalChordType.AugPer:
            return 'AugPer'
        
    @staticmethod
    def to_type(t_string):
        t = None
        if t_string == 'PerPer':
            t = QuartalChordType.PerPer
        if t_string == 'PerAug':
            t = QuartalChordType.PerAug
        if t_string == 'AugPer':
            t = QuartalChordType.AugPer
        return QuartalChordType(t) if t is not None else None
        
    def __eq__(self, y):
        return self.value == y.value
    
    def __hash__(self):
        return self.__str__().__hash__()


class QuartalChordTemplate(ChordTemplate):
    """
    Template for quartal chords.  Quartal chords are based on incremental intervals of perfect and augmented intervals.
    This follows along the lines of Persechetti.  We do not used diminished 4th as they identify more with major 3rds.  
    
    We have a regular expression syntax to cover these cases that roughly goes:

    (Q|q)((I|II|...)|A-G)((PerPer|PerAug|AugPer| ...)|(m|M)+))?(@([1-9]([0-9]*)))?
    
    Examples:
      QII
      qCpapa
    """
    
    QUARTAL_CHORD_TYPE_MAP = {
        QuartalChordType.PerPer: [IntervalN(1, IntervalType.Perfect),
                                  IntervalN(4, IntervalType.Perfect),
                                  IntervalN(4, IntervalType.Perfect)],
        QuartalChordType.PerAug: [IntervalN(1, IntervalType.Perfect),
                                  IntervalN(4, IntervalType.Perfect),
                                  IntervalN(4, IntervalType.Augmented)],
        QuartalChordType.AugPer: [IntervalN(1, IntervalType.Perfect),
                                  IntervalN(4, IntervalType.Augmented),
                                  IntervalN(4, IntervalType.Perfect)],
    }

    GROUP_BASIS = 'Basis'
    GROUP_BASIS_TAG = '?P<' + GROUP_BASIS + '>'
    P1_BASIS = '(' + GROUP_BASIS_TAG + 'Q|q)?'
    
    SCALE_DEGREE = 'III|II|IV|VII|VI|V|I|iii|ii|iv|vii|vi|v|i'
    GROUP_SCALE_DEGREE = 'ScaleDegree'
    GROUP_SCALE_DEGREE_TAG = '?P<' + GROUP_SCALE_DEGREE + '>'    
    
    GROUP_DIATONIC_TONE = 'DiatonicTone'
    GROUP_DIATONIC_TONE_NAME = '?P<' + GROUP_DIATONIC_TONE + '>' 
    ROOT = '((' + GROUP_DIATONIC_TONE_NAME + DiatonicTone.DIATONIC_PATTERN_STRING + ')|' + \
           '(' + GROUP_SCALE_DEGREE_TAG + SCALE_DEGREE + '))'

    CHORD_NAMES = 'PerPer|PerAug|AugPer'
    GROUP_CHORD = 'Chord'
    GROUP_CHORD_TAG = '?P<' + GROUP_CHORD + '>'  
    
    SECONDS = 'Seconds'
    SECONDS_SPECIFICATION_TAG = '?P<' + SECONDS + '>' 
    CHORDS = '((' + GROUP_CHORD_TAG + CHORD_NAMES + ')|(' + SECONDS_SPECIFICATION_TAG + '(p|P|a|A)+))?'
    
    INVERSION = '[1-9]([0-9]*)'
    GROUP_INVERSION = 'Inversion'
    GROUP_INVERSION_TAG = '?P<' + GROUP_INVERSION + '>'
    INVERSIONS = '(\\@(' + GROUP_INVERSION_TAG + INVERSION + '))?'
    
    # full parse string and accompanying pattern for the secundal chord grammar.
    QUARTAL_PARSE_STRING = P1_BASIS + ROOT + CHORDS + INVERSIONS + '$'
    QUARTAL_PATTERN = re.compile(QUARTAL_PARSE_STRING)

    def __init__(self, diatonic_basis, scale_degree, chord_type, specified_fourths, inversion):
        """
        Constructor
        
        Args:
          diatonic_basis: DiatonicTone used as root of chord, e.g. C major chord, the C part
          scale_degree: int version of roman numeral
          chord_type: The chord type ala SecundalChordType
          specified_fourths: list of incremental fourth IntervalN's comprising the chord, e.g. [p, P, P]
                             usually used in lieu of, or addition to chord_type chord_type
          inversion: int for which of the chord tones (ordinal) serves as root [origin 1]
        """
        ChordTemplate.__init__(self)
        self.__diatonic_basis = diatonic_basis   # DiatonicTone
        
        self.__scale_degree = scale_degree   
        
        self.__chord_type = chord_type  
        self.__inversion = inversion    # which tone of n is the bass
        
        self.__base_intervals = []
        if chord_type:
            self.__base_intervals.extend(QuartalChordTemplate.QUARTAL_CHORD_TYPE_MAP[chord_type.value])
        self.__specified_fourths = specified_fourths
        if specified_fourths:
            intervals = list()
            intervals.append(IntervalN(1, IntervalType.Perfect))
            for ltr in specified_fourths:
                intervals.append(IntervalN(4, IntervalType.Perfect if ltr == 'P' or ltr == 'p'
                                          else IntervalType.Augmented))
            self.__base_intervals.extend(intervals)
                 
        # Inversion check - only if chord type was given, not for cases like II
        if self.chord_type and self.inversion > len(self.base_intervals):
            raise Exception('Illegal inversion {0} for {1}'.format(self.inversion, self.__str__()))

    @property
    def diatonic_basis(self):
        return self.__diatonic_basis
     
    @property   
    def scale_degree(self):
        return self.__scale_degree
    
    @property
    def chord_type(self):
        return self.__chord_type
    
    @property
    def base_intervals(self):
        return self.__base_intervals
    
    @property
    def inversion(self):
        return self.__inversion
    
    @property
    def specified_fourths(self):
        return self.__specified_fourths
        
    def create_chord(self, diatonic_tonality=None):
        return QuartalChord(self, diatonic_tonality) 
    
    @staticmethod
    def get_chord_type(interval_list):
        for k, v in list(QuartalChordTemplate.QUARTAL_CHORD_TYPE_MAP.items()):
            if len(interval_list) == len(v):
                same = True
                for i in range(0, len(v)):
                    if not interval_list[i].is_same(v[i]):
                        same = False
                        break
                if same:
                    return QuartalChordType(k)
                
        # Build a M/m string
        t = ''
        for interval in interval_list[1:]:
            if interval.interval_type == IntervalType.Perfect:
                t += 'P'
            elif interval.interval_type == IntervalType.Augmented:
                t += 'A'
            else:
                raise Exception('Illegal interval type for quartal {0}'.format(interval))
        return t
        
    def __str__(self):
        return 'Q{0}{1}{2}{3}'.format(self.diatonic_basis.diatonic_symbol if self.diatonic_basis else
                                      (str(ChordTemplate.SCALE_DEGREE_REVERSE_MAP[self.scale_degree])),
                                      self.chord_type if self.chord_type else
                                      (self.specified_fourths if self.specified_fourths else ''),
                                      '@' + str(self.inversion) if self.inversion != 1 else '',
                                      ' --> ' + (' '.join(str(w) for w in self.base_intervals)),)
     
    @staticmethod   
    def parse(chord_string):
        """
        Parse an input string into a QuartalChordTemplate.
        
        Args:
          chord_string: string input representing chord
        Returns:
          QuartalChordTemplate       
        """
        if not chord_string:
            raise QuartalChordException('Unable to parse chord string to completion: {0}'.format(chord_string))
        m = QuartalChordTemplate.QUARTAL_PATTERN.match(chord_string)
        if not m:
            raise QuartalChordException('Unable to parse chord string to completion: {0}'.format(chord_string))
        
        scale_degree = m.group(QuartalChordTemplate.GROUP_SCALE_DEGREE)
        if scale_degree:
            scale_degree = ChordTemplate.SCALE_DEGREE_MAP[scale_degree]
        if m.group(QuartalChordTemplate.GROUP_DIATONIC_TONE) is not None:
            diatonic_basis = DiatonicTone(m.group(QuartalChordTemplate.GROUP_DIATONIC_TONE))
        else:
            diatonic_basis = None
        chord_name = m.group(QuartalChordTemplate.GROUP_CHORD)
        chord_type = None
        if chord_name:
            chord_type = QuartalChordType.to_type(chord_name)
      
        fourths = m.group(QuartalChordTemplate.SECONDS) 
        inversion_text = m.group(QuartalChordTemplate.GROUP_INVERSION)
        inversion = int(inversion_text) if inversion_text else 1
        
        logging.info('{0}, {1}, {2}, {3}'.format(diatonic_basis if scale_degree is None else str(scale_degree),
                                                 str(chord_type) if chord_type else '',
                                                 fourths if fourths else '',
                                                 inversion))
        return QuartalChordTemplate(diatonic_basis, scale_degree, chord_type, fourths, inversion)

# ==============================================================================
# ============================================================================== 11
# ==============================================================================
class Singleton(object):

    _instances = {}  # sdict of global class instances: mapping class type to class instance.

    @classmethod
    def instance(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls]  = cls(*args, **kwargs)
        return cls._instances[cls]

# ==============================================================================
class InstrumentBase(object):
    """
    This class is a base class for all classes in the instrument catalog tree.
    It takes case of details such as:
    *) Management of parent
    *) Holds the name as a property
    *) Holds the articulation set.
    
    The articulation is cumulative through parentage - using the tree with specifics at the lowest level
    and general articulations at the higher level.
    """

    def __init__(self, name, parent=None):
        """
        Constructor
        Args:
        name: (String)
        parent: (InstrumentBase) of the parent node; None is no parent.
        """
        self.__name = name
        self.__parent = parent
        
        self.__articulations = []
        
    @property
    def name(self):
        return self.__name
    
    @property
    def parent(self):
        return self.__parent
    
    def get_native_articulations(self):
        return list(self.__articulations)
    
    def add_articulation(self, articulation):
        self.__articulations.append(articulation)
        
    def extend_articulations(self, articulation_list):
        self.__articulations.extend(articulation_list)

    @property
    def articulations(self):
        return self.__articulations

    @articulations.setter
    def articulations(self, articulation_list):
        self.__articulations = list()
        self.__articulations.extend(articulation_list)

    def get_articulations(self):
        """
        Get the list of articulations from this level and up.
        """
        art_list = self.get_native_articulations()
        parent = self.parent
        while parent is not None:
            art_list.extend(parent.get_native_articulations())
            parent = parent.parent
            
        return art_list

# ==============================================================================
class InstrumentClass(InstrumentBase):
    """
    Class to identify a broad instrument type, e.g.  stringw, woodwinds, bass, percussion, keyboards.
    """

    def __init__(self, name, parent=None):
        """
        Constructor.
        
        Args:
          name: (String) name of class, e.g. woodwinds, strings
        """
        
        InstrumentBase.__init__(self, name, parent)
        
        self.__families = []
            
    @property
    def families(self):
        return list(self.__families)
    
    def add_family(self, family):
        self.__families.append(family)
        
    def __str__(self):
        return '{0}'.format(self.name)

# ==============================================================================
class InstrumentFamily(InstrumentBase):
    """
    Class designating an specific instrument genera, e.g. Clarinet, having  Clarinet Bb, Eb, etc. 
    """

    def __init__(self, name, parent=None):
        """
        Constructor.
        
        Args:
          name: (String) name of family, e.g. Clarinets
        """
        InstrumentBase.__init__(self, name, parent)
        
        self.__instruments = []
    
    @property 
    def instruments(self):
        return list(self.__instruments)   
       
    def add_instrument(self, instrument):
        self.__instruments.append(instrument)
        
    def __str__(self):
        return '{0}'.format(self.name)

# ==============================================================================
class Instrument(InstrumentBase):
    """
    Class defining a particular instrument, including it written and sounding pitch ranges.
    """

    def __init__(self, name, key, low, high, transpose_up, transpose_interval, parent=None):
        """
        Constructor
        
        Args:
        name:  (String)
        key:   (String) key of the instrument
        low:   (String) low written pitch
        high:  (String) high written pitch
        transpose_up: (boolean) transpose up if true
        transpose_interval: (interval) transpose interval to the diatonic foundation.
        parent:  (InstrumentBase) parent node in tree.
        """
        InstrumentBase.__init__(self, name, parent)
        
        self.__written_low = DiatonicPitch.parse(low)
        self.__written_high = DiatonicPitch.parse(high)
        self.__key = key if key else '' 
        self.__transpose_up = transpose_up 
        self.__transpose_interval = transpose_interval 
        
        # Compute the sounding range for this instrument.
        if self.transpose_interval:
            self.__sounding_low = self.transpose_interval.get_end_pitch(self.written_low) if self.transpose_up else \
                self.transpose_interval.get_start_pitch(self.written_low)
            self.__sounding_high = self.transpose_interval.get_end_pitch(self.written_high) if self.transpose_up else \
                self.transpose_interval.get_start_pitch(self.written_high)
        else:
            self.__sounding_low = self.written_low
            self.__sounding_high = self.written_high
    
    @property
    def key(self):
        return self.__key
    
    @property
    def written_low(self):
        return self.__written_low
    
    @property
    def transpose_up(self):
        return self.__transpose_up
    
    @property
    def transpose_interval(self):
        return self.__transpose_interval
    
    @property
    def written_high(self):
        return self.__written_high
    
    @property
    def sounding_low(self):
        return self.__sounding_low
    
    @property
    def sounding_high(self):
        return self.__sounding_high

    def sounding_pitch_range(self):
        return PitchRange(self.sounding_low.chromatic_distance,
                          self.sounding_high.chromatic_distance)

    def written_pitch_range(self):
        return PitchRange(self.written_low.chromatic_distance,
                          self.written_high.chromatic_distance)

    def __str__(self):
        first = '{0} [{1}-{2}]'.format(self.name, self.written_low, self.written_high)
        
        if self.transpose_interval:
            second = ' {0} {1} [{2}-{3}]'.format(('up' if self.transpose_up else 'down'), self.transpose_interval,
                                                 self.sounding_low, self.sounding_high)
        else:
            second = ''
            
        return first + second

# ==============================================================================
class Articulation(object):
    """
    Define a representative class for articulations.
    """

    def __init__(self, name):
        """
        Constructor.

        Args:
            name: String name of articulation.
        """
        self.__name = name
        
    @property
    def name(self):
        return self.__name
    
    def __str__(self):
        return '{0}'.format(self.name)
    
# ==============================================================================
class InstrumentCatalog(InstrumentBase, Singleton):
    """
    InstrumentCatalog is a singleton object that acts as the root node to a set of musical instruments.
    The details of the instruments are found in 'instruments.xml'.  This class reads that file and 
    populates the catalog with appropriate class instances:
      InstrumentClass: representing an instrument genre such as woodwinds, bass, etc
      InstrumentFamily: representing a type of instrument that may have several variants, e.g. clarinet
      Instrument: representing the instrument itself and carries details about that instrument. 
    """
    
    DATA_DIRECTORY = 'data'
    # Name of the file sound in ./data
    INSTRUMENT_FILE = 'instruments.xml'

    def __init__(self, *args,  **kwargs):
 
        InstrumentBase.__init__(self, '', None)

        xml_file = kwargs.get('xml_file', None)

        tree = None
        if xml_file is None:
            this_dir, this_filename = os.path.split(__file__)
            data_path = os.path.join(this_dir, InstrumentCatalog.DATA_DIRECTORY)
            tree = ElementTree.parse(os.path.join(data_path, InstrumentCatalog.INSTRUMENT_FILE))
        elif isinstance(xml_file, str):
            if len(xml_file) != 0:
                dirr, fn = os.path.split(xml_file)
                tree = ElementTree.parse(os.path.join(dirr, fn))
        
        self.inst_classes = []
        
        self.articulations = []
        
        # maps instrument name to instrument.
        self.instrument_map = {}
        
        # maps instrument family name to a list of all the instrument members of that family.
        self.instrument_family_map = {}

        if tree is not None and (xml_file is None or len(xml_file) != 0):
            root = tree.getroot()
            self._parse_structure(root)
        
            self._build_maps()
        
    def _parse_structure(self, root):
        for child in root:
            if child.tag == "InstrumentClasses":
                self._parse_classes(child)
            elif child.tag == "Articulations":
                self.articulations = InstrumentCatalog._parse_articulations(child)
        
    def _parse_classes(self, class_root):
        for inst_class in class_root:
            logging.info("{0} {1}".format(inst_class.tag, inst_class.get('name')))
            current_inst_class = InstrumentClass(inst_class.get('name'), self)
            self.inst_classes.append(current_inst_class)
            
            for child_attr in inst_class:
                if child_attr.tag == 'InstrumentGroup':             
                    # article is either an InstrumentFamily, or an Instrument
                    for article in child_attr:  
                        logging.info("   {0}, {1}".format(article.tag, article.attrib))
                        current_family = InstrumentFamily(article.get('name'), current_inst_class)
                        current_inst_class.add_family(current_family)
                        if article.tag == 'InstrumentFamily':                   
                            for inst in article:  
                                logging.info("       {0}, {1}".format(inst.tag, inst.attrib)) 
                                current_family.add_instrument(self.create_instrument(inst, current_family))
                        else:
                            current_family.add_instrument(self.create_instrument(article, current_family))
                elif child_attr.tag == 'Articulations':
                    current_inst_class.extend_articulations(InstrumentCatalog._parse_articulations(child_attr))

    @staticmethod
    def _parse_articulations(articulation_root):
        articulation_list = []
        for articulation in articulation_root:
            articulation_list.append(Articulation(articulation.get('name'))) 
        return articulation_list

    @staticmethod
    def create_instrument(inst_node, parent):
        low = high = ''
        up_down = None
        transpose_interval = None
        articulations = []
        for c in inst_node:
            if c.tag == 'Range':
                for lh in c:
                    if lh.tag == 'Low':
                        low = lh.text
                    elif lh.tag == 'High':
                        high = lh.text  
            elif c.tag == 'Transpose':
                updown_txt = c.get('direction') 
                if updown_txt != 'up' and updown_txt != 'down':
                    raise Exception(
                        'Illegal transpose up/down must be \'up\' or \'down\'  now \'{0}\''.format(updown_txt))
                up_down = updown_txt == 'up'
                transpose_interval = IntervalN.parse(c.get('interval'))
            elif c.tag == 'Articulations':
                articulations = InstrumentCatalog._parse_articulations(c)
                
        instrument = Instrument(inst_node.get('name'), inst_node.get('key'), low, high, up_down,
                                transpose_interval, parent)
        instrument.extend_articulations(articulations)
        return instrument
    
    def _build_maps(self):
        self.instrument_map = {}
        self.instrument_family_map = {}

        for inst_class in self.inst_classes:
            families = inst_class.families
            for family in families:
                instruments = family.instruments
                self.instrument_family_map[family.name.upper()] = instruments
                for instrument in instruments:
                    self.instrument_map[instrument.name.upper()] = instrument
                    
    def get_instrument(self, name):
        return self.instrument_map[name.upper()] if name.upper() in self.instrument_map else None
    
    def get_instruments(self, name):
        return self.instrument_family_map[name.upper()] if name.upper() in self.instrument_map else None
    
    def instrument_classes(self):
        return list(self.inst_classes)

    def add_instrument_class(self, instrument_class):
        self.inst_classes.append(instrument_class)
        self._build_maps()

    def print_catalog(self):
        for inst_class in self.inst_classes:
            print(inst_class)
            for family in inst_class.families:
                print('    ', family)
                for instrument in family.instruments:
                    print('    ', '    ', instrument)

# ==============================================================================
# ============================================================================== 12
# ==============================================================================

class DynamicsEvent(Event):
    """
    Event based on Dynamics
    """

    def __init__(self, dynamics, time):
        """
        Constructor.
        
        Args:
          dynamics: (Dynamics) object.
          time: Comparable object.
        """
        Event.__init__(self, dynamics, time)
        
        if dynamics is None or not isinstance(dynamics, Dynamics):
            raise Exception('Dynamics event argument must be not null and Dynamics')
        
    def velocity(self):
        return self.object.velocity
    
    def __str__(self):
        return '[{0}, Dynamics({1})]'.format(self.time, self.object)
    
    def dynamics(self):
        return self.object

# ==============================================================================
class DynamicsHelper:
    NAME_MAP = None
    DYNAMICS_VALUE_MAP = None
    DEFAULT_DYNAMICS = None
    DEFAULT_DYNAMICS_VELOCITY = None
    REVERSE_DYNAMICS_VELOCITY_MAP = None
    DYNAMICS_LIST = None


class Dynamics(Enum):
    """
    Class representing music dynamics.  We use PPPP through FFFF.
    Velocity values have been assigned based on 0-127 midi range.
    """
    PPPP = 1
    PPP = 2
    PP = 3
    P = 4
    MP = 5
    MF = 6
    F = 7
    FF = 8
    FFF = 9
    FFFF = 10

    def __str__(self):
        return self.name

    @staticmethod
    def class_init():
        if DynamicsHelper.NAME_MAP is not None:
            return
    
        DynamicsHelper.NAME_MAP = {
            Dynamics.PPPP:  'pianissississimo',
            Dynamics.PPP:   'pianississimo0',
            Dynamics.PP:    'pianissimo',
            Dynamics.P:     'piano',
            Dynamics.MP:    'mezzo piano',
            Dynamics.MF:    'messo forte',
            Dynamics.F:     'forte',
            Dynamics.FF:    'fortissimo',
            Dynamics.FFF:   'fortississimo',
            Dynamics.FFFF:  'fortissississimo',
        }
    
        DynamicsHelper.DYNAMICS_VALUE_MAP = {
            Dynamics.PPPP:  16,
            Dynamics.PPP:   24,
            Dynamics.PP:    33,
            Dynamics.P:     49,
            Dynamics.MP:    64,
            Dynamics.MF:    80,
            Dynamics.F:     96,
            Dynamics.FF:    112,
            Dynamics.FFF:   120,
            Dynamics.FFFF:  127,
        }

        DynamicsHelper.DYNAMICS_LIST = [
            Dynamics.PPPP,
            Dynamics.PPP,
            Dynamics.PP,
            Dynamics.P,
            Dynamics.MP,
            Dynamics.MF,
            Dynamics.F,
            Dynamics.FF,
            Dynamics.FFF,
            Dynamics.FFFF,
        ]
    
        DynamicsHelper.DEFAULT_DYNAMICS = Dynamics.MP
        DynamicsHelper.DEFAULT_DYNAMICS_VELOCITY = DynamicsHelper.DYNAMICS_VALUE_MAP[DynamicsHelper.DEFAULT_DYNAMICS]
        DynamicsHelper.REVERSE_DYNAMICS_VELOCITY_MAP = OrderedMap({value: key for (key, value) in
                                                                   DynamicsHelper.DYNAMICS_VALUE_MAP.items()})

    @property
    def velocity(self):
        return DynamicsHelper.DYNAMICS_VALUE_MAP[self]
    
    @staticmethod
    def nearest_dynamics(value):
        """
        Return the nearest dynamics for a given velocity value.
        
        Args:
          value:  The velocity value.
        Returns: The nearest Dynamics as a Dynamics object.
        """
        if value <= Dynamics.DYNAMICS_VALUE_MAP[Dynamics.PPPP]:
            return Dynamics.PPPP
        if value >= Dynamics.DYNAMICS_VALUE_MAP[Dynamics.FFFF]:
            return Dynamics.FFFF
        d = Dynamics.REVERSE_DYNAMICS_VELOCITY_MAP.floor(value) 
        next_d = d.keys()[d.keys().index(d) + 1]
        return Dynamics(Dynamics.REVERSE_DYNAMICS_VELOCITY_MAP[d] if value <= (d + next_d)/2 else
                        Dynamics.REVERSE_DYNAMICS_VELOCITY_MAP[next_d])

    def __eq__(self, y):
        return self.value == y.value
    
    def __hash__(self):
        return hash(self.name)   
    
    @staticmethod
    def get_types():
        return [DynamicsHelper.DYNAMICS_LIST]

    @staticmethod
    def DEFAULT_DYNAMICS_VELOCITY():
        return DynamicsHelper.DEFAULT_DYNAMICS_VELOCITY
    
    @staticmethod
    def get_velocity_for(dynamics):
        """
        Static method to get the range for a tempo type.
        Args:
          dynamics: if integer, turned into Dynamics based on int.  Otherwise must be a Dynamics.
          
        Returns: velocity for type.
        Exception: on bad argument type.
        """
        if isinstance(dynamics, int):
            if dynamics < 1 or dynamics > len(DynamicsHelper.DYNAMICS_LIST):
                raise Exception('Out of range int for get_velocity_for {0}'.format(type(dynamics)))
            dynamics = DynamicsHelper.DYNAMICS_LIST[dynamics - 1]
        elif not isinstance(dynamics, Dynamics):
            raise Exception('Illegal argument type for get_velocity_for {0}'.format(type(dynamics)))
        return dynamics.velocity


# Initialize the static tables in the Dynamics class.
Dynamics.class_init()

# ==============================================================================
class DynamicsFunction(object):
    """
    A functional wrapper for Dynamics. Constructs a constant function for a given Dynamics setting, or Rational setting,
        otherwise uses the given function for evaluation.
    """

    def __init__(self, dynamics_or_function):
        """
        Constructor
        
        Args: (Dynamics, Rational, or Function)
        """
        if isinstance(dynamics_or_function, Dynamics):
            self.fctn = ConstantUnivariateFunction(dynamics_or_function.velocity, 0, 1)
        elif isinstance(dynamics_or_function, Rational):
            self.fctn = ConstantUnivariateFunction(dynamics_or_function, 0, 1)
        elif isinstance(dynamics_or_function, UnivariateFunction):
            self.fctn = dynamics_or_function
        else:
            raise Exception('Illegal argument type {0)', type(dynamics_or_function))
                        
    def velocity(self, offset, duration):
        """
        Compute a velocity setting based on a given offset on domain defined by duration
        The offset is rescaled to the actual range of the function.
        
        Args:
          offset: (Offset) within duration
          duration: (Duration) of domain
        """
        # scale to functions domain
        q = (offset.offset/duration.duration) * (convert_to_numeric(self.fctn.domain_end) -
                                                 convert_to_numeric(self.fctn.domain_start))
        return self.fctn.eval(convert_to_numeric(self.fctn.domain_start) + q)
    
    def function_range(self):
        return self.fctn.domain_end - self.fctn.domain_start
    
    def dynamics(self, offset, duration):
        """
        Compute the velocity as a Dynamics setting.
        
         Args:
           offset: (Offset) within duration
           duration: (Duration) of domain
        """
        v = self.velocity(offset, duration)
        return Dynamics.nearest_dynamics(v)
    
    def __str__(self):
        return '[DyFctn({})]'.format(self.fctn)
    
# ==============================================================================
class DynamicsFunctionEvent(Event):
    """
    Event class for events that represent a dynamics or a dynamics function.
    """

    def __init__(self, dynamics_or_function, time):
        """
        Constructor
        
        Args:
          dynamics_or_function: Either a Dynamics setting or a Function
        """
        objct = DynamicsFunction(dynamics_or_function)
        Event.__init__(self, objct, time)
        
    def velocity(self, position, next_event_position):
        """
        Compute the velocity at a given position (re: DynamicsEventSequence)
        
        Args:
          position: The absolute position (Position) to evaluate at
          next_event_position:  The position (Position) of the starting of the next event.  Can be None is none exists.
        Returns:
          velocity as numerics [0-127] typically
        """
        return self.object.velocity(Offset(position.position - self.time.position),
                                    next_event_position - self.time if next_event_position else Duration(1))
    
    def dynamics(self, position, next_event_position):
        """
        Compute the velocity at a given position (re:DynamicsEventSequence.
        
        Args:
          position: The absolute position (Position) to evaluate at
          next_event_position:  The position (Position) of the starting of the next event.  Can be None is none exists,
          function range is used.
        Returns:
          velocity as Dynamics position
        """
        return self.object.dynamics(
            position - self.time, next_event_position - self.time if next_event_position else
            self.object.function_range())

# ==============================================================================
class DynamicsEventSequence(EventSequence):
    """
    Specialization of event sequence for dynamics.
    """

    def __init__(self, event_list=None):
        """
        Constructor.

        Args:
            event_list: list of events to initialize the sequence
        """
        EventSequence.__init__(self, event_list)
        
    def velocity(self, position):
        dfe = self.floor_event(position)
        if isinstance(dfe, DynamicsFunctionEvent):
            next_dfe = self.successor(dfe)
            return dfe.velocity(position, next_dfe.time if next_dfe is not None else None)
        else:
            return dfe.velocity()

# ==============================================================================
class IntervalTree(object):
    """
    IntervalTree is a class that uses the RB-Tree algorithms, but modified to a useful search means over
    intervals over a real line.  This implementation is based on Cormen, et. al. Algorithms.
    Some modification were made to that algorithm to, for example, allow multiple node deletions.
    """

    def __init__(self):
        """
        Constructor.
        """
        
        # A nil RBNode is used in lieu of None as indicated in Corman that it
        # facilitates the algorithm details.
        self.__nil = RBNode()
        
        # And nil is currently the root.
        self.__root = self.nil
        
        self.__node_id_gen = 1
        
    def gen_node_id(self):
        # __node_gen_id is used to generate a unique identifying integer, per tree, per RBNode.
        self.__node_id_gen += 1
        return self.__node_id_gen
     
    @property
    def root(self):
        return self.__root
    
    @property
    def nil(self):
        return self.__nil
     
    @root.setter
    def root(self, root_node):
        self.__root = root_node 
        
    def _tree_insert(self, node):
        y = self.nil
        x = self.root
        while x != self.nil:
            y = x
            if node.key < x.key:
                x = x.left
            else:
                x = x.right
    
        node.parent = y
        if y == self.nil:
            self.root = node
        else:
            if node.key < y.key:
                y.left = node
            else:
                y.right = node
      
    def put(self, interval, value):
        node = RBNode(interval, value, self)
    
        self._tree_insert(node)
        node.apply_update()
    
        node.color = RBNode.Red
        while node != self.root and node.parent.color == RBNode.Red:
            if node.parent == node.parent.parent.left:
                y = node.parent.parent.right
                if y != self.nil and y.color == RBNode.Red:
                    node.parent.color = RBNode.Black
                    y.color = RBNode.Black
                    node.parent.parent.color = RBNode.Red
                    node = node.parent.parent
                else:
                    if node == node.parent.right:
                        node = node.parent
                        node.left_rotate()
                    node.parent.color = RBNode.Black
                    node.parent.parent.color = RBNode.Red
                    node.parent.parent.right_rotate()
            else:
                y = node.parent.parent.left
                if y != self.nil and y.color == RBNode.Red:
                    node.parent.color = RBNode.Black
                    y.color = RBNode.Black
                    node.parent.parent.color = RBNode.Red
                    node = node.parent.parent
                else:
                    if node == node.parent.left:
                        node = node.parent
                        node.right_rotate()
                    node.parent.color = RBNode.Black
                    node.parent.parent.color = RBNode.Red
                    node.parent.parent.left_rotate()
    
        self.root.color = RBNode.Black 
        
        return node
        
    def query_point(self, point):
        """
        Query for all intervals that intersect a point.
        
        Args:
          point: Number to be queried about
          
        Returns:
          The answer list of IntervalInfo's
        """
        if self.root == self.nil:
            return []  
        return self.root.query_point(point, [])
  
    def query_interval(self, interval):
        """
        Query for all intervals that intersect a given interval.
        
        Args:
          interval: The Interval to check intersection against
        
        Returns:
          The answer list of IntervalInfo's
        """
        return self.root.query_interval(interval, [])
    
    def find_exact_interval(self, interval):
        """
        Find all results (intervals via IntervalInfo's) that match a given interval.
        
        Args:
          interval: Interval to find
        Returns:
          List of IntervalInfo's that match the interval exactly.
        """
        
        mid_value = (interval.upper + interval.lower) * Fraction(1, 2)
        mid = Position(mid_value) if isinstance(mid_value, numbers.Rational) or isinstance(mid_value, Fraction) else \
            mid_value

        results = self.query_point(mid)
        ret_results = []
        for result in results:
            if result.interval == interval:
                ret_results.append(result)
        return ret_results
    
    def query_interval_start(self, interval):
        """
        Find all results (intervals via IntervalInfo's that start in given interval
        
        Args:
          interval: Interval to find
        Returns:
          List of IntervalInfo's that start in given interval.
        """
        answer = []
        if self.root != self.nil:
            self.root.query_interval_start(interval, answer)
        return answer
    
    def delete(self, interval_info):
        """
        Delete an interval from the interval tree.  
        
        Args:
          interval_info: IntervalInfo that had been acquired from a search.
        """
        self.root.delete_node(interval_info.rb_node)
    
    def intervals(self): 
        return self.root.intervals([])

    def intervals_and_values(self):
        return self.root.intervals_and_values([])
    
    def tree_minimum(self):
        return self.root.node_minimum()
    
    def tree_maximum(self):
        return self.root.node_maximum()
      
    def print_tree(self):
        if not self.root:
            return ''
        base = 'root = [{0}] \n'.format(self.root.id)
        return base + self.root.print_tree()
    
    def __str__(self):
        return self.print_tree()
    
# ==============================================================================
class Voice(Observer):
    """
    Voice is a Line with two key attributes:
    1) Instrument that 'plays' this voice.
    2) Interval tree to enable fast searches for notes in the Voice.
    
    Voice can only add Lines, and the interval tree covers all the notes in the contained lines.
    """

    def __init__(self, instrument):
        """
        Constructor.
        
        Note: there are several interesting questions here.
           1) should Line.__init__ be called first.  Because the init coult call overridden methods, e.g. duration
           2) should Voice be limited to Line membership only?
        """
        Observer.__init__(self)
        
        self.__instrument = instrument
                  
        self.__lines = []
        self.interval_tree = IntervalTree()  
        
        # map notes to their articulation
        self.articulation_map = {}  
        
        # Sequence of event related to setting dynamics
        self.__dynamics_sequence = DynamicsEventSequence()
           
    @property
    def lines(self):
        return list(self.__lines)
    
    @property
    def instrument(self):
        return self.__instrument
    
    @property
    def duration(self):
        return self.length()
    
    def length(self):
    #    from misc.utility import convert_to_numeric
    #    from fractions import Fraction
        last = Fraction(0)
        for line in self.lines:
            ep = convert_to_numeric(line.relative_position + line.length())
            if ep > last:
                last = ep
        return Duration(last) 
    
    def assign_articulation(self, note, articulation):
        if not self.note_belongs_to_voice(note):
            raise Exception("Note {0} does not belong to voice".format(note))
        self.articulation_map[note] = articulation
        
    def get_articulation(self, note):
        if note in self.articulation_map:
            return self.articulation_map[note]
        return None
    
    def get_velocity(self, position):
        dynamics_event = self.dynamics_sequence.floor_event(position)
        if not dynamics_event:
            return Dynamics.DEFAULT_DYNAMICS_VELOCITY()
        if isinstance(dynamics_event, DynamicsEvent):
            return dynamics_event.velocity()
        else:
            next_dfe = self.dynamics_sequence.successor(dynamics_event)
            return dynamics_event.velocity(position, next_dfe.time if next_dfe else Position(self.length().duration))
    
    @property
    def dynamics_sequence(self):
        return self.__dynamics_sequence
    
    def coverage(self):
        """
        Returns the WNT coverage interval for voice.
        """
        return self.interval_tree.root.coverage()
        
    def pin(self, line, offset=Offset(0)):
        """
        Overrides Line.pin.  The differences is that only a Line can be added with notes starting at 'offset'
        to the beginning of the line.
        
        Args:
          line:  Line to be added
          offset:  (Offset) into Voice to add the line.
        """
        if not isinstance(line, Line):
            raise Exception('Voice can only pin Line\'s, {0} received'.format(type(line)))
        
        if line not in self.__lines:
            self.__lines.append(line)
            line.register(self)
        else:
            self._remove_notes_from_tree(line.get_all_notes())
            
        line.relative_position = offset
        
        # add all the individual notes to the interval_tree
        #  NOTE: don't do this twice!!!
        self._add_notes_to_tree(line.get_all_notes())
        
    def unpin(self, line):
        if not isinstance(line, Line):
            raise Exception('Voice can only unpin Line\'s, {0} received'.format(type(line)))
        if line not in self.__lines:
            raise Exception('Voice can only unpin lines it owns')
        self.__lines.remove(line)
        line.relative_position = Offset(0)
        line.deregister(self)
        
        self._remove_notes_from_tree(line.get_all_notes())
            
    def _add_notes_to_tree(self, notes):
        for note in notes:
            
            # check of note is in range of the voice's instrument..
            if note.diatonic_pitch.chromatic_distance < self.instrument.sounding_low.chromatic_distance or \
               note.diatonic_pitch.chromatic_distance > self.instrument.sounding_high.chromatic_distance:
                raise Exception('Note {0} not in instrument {1} sounding range'.format(note, self.instrument)) 
            
            interval = Interval(note.get_absolute_position(), 
                                note.get_absolute_position() + note.duration)
            self.interval_tree.put(interval, note)
            
    def _remove_notes_from_tree(self, notes):
        # remove all intervals from the old line
        for note in notes:
            interval = Interval(note.get_absolute_position().position, 
                                note.get_absolute_position().position + note.duration.duration)
            result = self.interval_tree.find_exact_interval(interval)
            for interval_info in result:
                if interval_info.value == note:
                    self.interval_tree.delete(interval_info)  
                    
            if note in self.articulation_map:
                del self.articulation_map[note]      
            
    def get_notes_by_interval(self, interval, line=None):
        """
        Get all notes in the voice whose position/duration intersect with a given interval.
        
        Args:
          interval: given Interval.
          line: optional Line to restrict search to.
        Returns:
          List of notes satisfying query.
        """
        if line:
            if line not in self.__lines:
                return []
            notes = self.get_notes_by_interval(interval)
            return_val = [n for n in notes if Voice._find_line_by_note(n) == line]
            return_val.sort(key=lambda x: x.get_absolute_position())
            return return_val 
        else:
            result = self.interval_tree.query_interval(interval)
            notes = [info.value for info in result]
            notes.sort(key=lambda x: x.get_absolute_position())
            return notes
        
    def get_notes(self, start_position, end_position, line=None):
        """
        Get all notes in explicit interval given as lower/upper bounds, [)
        
        Args:
          start_position: Position of the start of the interval (inclusive)
          end_position: Position of the end of the interval (non-inclusive)
          line: Optionsl Line to restrict search to:
          
        Returns:
          List of notes satisfying query
        """
        return self.get_notes_by_interval(Interval(start_position, end_position), line)
    
    def get_notes_starting_in_interval(self, interval, line=None):
        """
        Get all notes that start in the given interval.
        
        Args:
          interval: Interval wherein return notes must begin.
          line: Optional Line to restrict search to.
        Returns:
          list of notes satisfying query.
        """
        if line:
            if line not in self.__lines:
                return []
            notes = self.get_notes_starting_in_interval(interval)
            return_val = [n for n in notes if Voice._find_line_by_note(n) == line]
            return_val.sort(key=lambda x: x.get_absolute_position())
            return return_val
        else:
            result = self.interval_tree.query_interval_start(interval)
            notes = [info.value for info in result]
            notes.sort(key=lambda x: x.get_absolute_position())
            return notes 

    @staticmethod
    def _find_line_by_note(note):
        p = note.parent
        while p is not None:
            if isinstance(p, Line):
                return p
            p = p.parent
        return None
    
    def note_belongs_to_voice(self, note):
        p = note.parent
        while p is not None:
            if p in self.__lines:
                return True
            p = p.parent
        return False

    def get_all_notes(self):
        notes = []
        for line in self.__lines:
            notes.extend(line.get_all_notes())
        return notes
    
    def notification(self,  observable, message_type, message=None, data=None):
    #    from structure.abstract_note import AbstractNote     
        if isinstance(observable, Line):
            if message_type == Line.LINE_NOTES_ADDED_EVENT: 
                self._add_notes_to_tree(Voice._extract_all_notes(data))
            elif message_type == Line.LINE_NOTES_REMOVED_EVENT:
                self._remove_notes_from_tree(Voice._extract_all_notes(data))
            elif message_type == AbstractNote.NOTES_ADDED_EVENT:
                self._add_notes_to_tree(Voice._extract_all_notes(data))

    @staticmethod
    def _extract_all_notes(data):
        notes = []
        note_input = data if isinstance(data, list) else [data]
        for s in note_input:
            notes.extend(s.get_all_notes())    
        return notes    
    
    def __str__(self):
        base = 'Voice(Dur({0}))'.format(self.duration)
        s = base + '[' + (']' if len(self.lines) == 0 else '\n')
        for n in self.lines:
            s += '  ' + str(n) + '\n'
        s += ']' if len(self.lines) != 0 else ''
        return s
    
# ==============================================================================
class InstrumentVoice(object):
    """
    A collection of Voices, each associated with the same instrument.
    """

    def __init__(self, instrument, num_voices=1):
        """
        Constructor.
        The InstrumentVoice retains the instrument, and creates a number of voice, number as specified in
        the constructor.  Each voice uses that instrument.

        Args:
            instrument: Instrument for the voice
            num_voices: Number of voices for this instrument.
        """
        
        self.__instrument = instrument
        self.__voices = [Voice(self.__instrument) for _ in range(num_voices)]
               
    @property
    def instrument(self):
        return self.__instrument
    
    @property
    def voices(self):
        return self.__voices
    
    @property
    def num_voices(self):
        return len(self.__voices)
    
    def voice(self, index):
        if index < 0 or index >= len(self.voices):
            raise Exception('Voice index {0} not in range [{1} -{2})'.format(index, 0, len(self.voices)))
        return self.voices[index]
    
    def get_notes_by_interval(self, interval):
        result = {}
        for i in range(0, self.num_voices):
            notes = self.voice(i).get_notes_by_interval(interval)
            result[self.voice(i)] = notes
        return result
    
    def get_notes_starting_in_interval(self, interval):
        result = {}
        for i in range(0, self.num_voices):
            notes = self.voice(i).get_notes_starting_in_interval(interval)
            result[self.voice(i)] = notes
        return result
    
    def get_all_notes(self):
        result = {}
        for i in range(0, self.num_voices):
            notes = self.voice(i).get_all_notes()
            result[self.voice(i)] = notes
        return result        
    
    @property
    def duration(self):
        return self.length()      
    
    def length(self):
        maxx = Duration(0, 1)
        for voice in self.__voices:
            d = voice.duration
            if d > maxx:
                maxx = d               
        return maxx  
    
    def __str__(self):
        return 'IV[{0}, {1}]'.format(self.instrument, self.num_voices)

# ==============================================================================
class TimeSignatureEventSequence(EventSequence):
    """
    An event sequence specialized to tempo events.
    """

    def __init__(self, event_list=None):
        """
        Constructor.

        Args:
            event_list: list of TempoEvents to initialize the sequence.
        """
        EventSequence.__init__(self, event_list)

    def time_signature(self, position):
        tfe = self.floor_event(position)
        return tfe.tempo()

# ==============================================================================
class UnivariateFunction(ABC):
    """
    Class that defines a generic (abstract) univariate function.
    """

    def __init(self):
        super().__init__()

    @abstractmethod
    def eval(self, v):
        """
        Evaluate the univariate function with input v, and return that value
        :param v: Typically some kind of numeric.
        :return:
        """
        pass
    
    @property
    @abstractmethod
    def domain_start(self):
        """
        Return the start value of the domain.
        :return:
        """
        pass

    @property
    @abstractmethod
    def domain_end(self):
        """
        Return the end value of the domain.
        :return:
        """
        pass

# ==============================================================================
class ConstantUnivariateFunction(UnivariateFunction):
    """
    Class defining a univarate function of constant value.
    """

    def __init__(self, value, domain_start, domain_end, restrict_domain=False):
        """
        Constructor.

        Args:
            value: the constant value
        domain_start: numeric-like that defines the start of a domain (first point)
        domain_end: numeric_like tat defines the end of a domain (last point)
        restrict_domain: boolean meaning to throw exception for evaluations outside the domain
        """
        self.value = value
        
        self.__domain_start = domain_start
        self.__domain_end = domain_end
        self.__restrict_domain = restrict_domain
        
    def eval(self, x):
        if self.restrict_domain:
            if x < self.domain_start or x > self.domain_end:
                raise Exception('out of range {0} [{1}, {2}]'.format(x, self.domain_start, self.domain_end))
        return self.value
    
    @property
    def domain_start(self):
        return self.__domain_start
        
    @property
    def domain_end(self):
        return self.__domain_end
    
    @property
    def restrict_domain(self):
        return self.__restrict_domain
    
    def __str__(self):
        return 'Function(cst, {0})'.format(self.value)

# ==============================================================================
def convert_to_numeric(value):
    if isinstance(value, Position):
        return value.position
    elif isinstance(value, Duration):
        return value.duration
    elif isinstance(value, Offset):
        return value.offset
    else:
        return value
    
# ==============================================================================
class TempoFunction(object):
    """
    A functional wrapper for Tempo. Constructs a constant function for a given Tempo setting, or Rational setting,
        otherwise uses the given function for evaluation.
    """

    def __init__(self, tempo_or_function, beat_duration=None):
        """
        Constructor
        .
        Args:
            tempo_or_function: Tempo for constant, Rational for constant, or UnivariateFunction.
            beat_duration: whole note time duration (Duration) for a beat.
        """
        if isinstance(tempo_or_function, Tempo):
            self.fctn = ConstantUnivariateFunction(tempo_or_function.tempo, 0, 1)
            if beat_duration:
                raise Exception('Cannot specify beat_duration with Tempo specified.')
            self.beat_duration = tempo_or_function.beat_duration
        elif isinstance(tempo_or_function, Rational):
            self.fctn = ConstantUnivariateFunction(tempo_or_function, 0, 1)
            if not beat_duration:
                beat_duration = Duration(1, 4)
            self.beat_duration = beat_duration
        elif isinstance(tempo_or_function, UnivariateFunction):
            self.fctn = tempo_or_function
            if not beat_duration:
                beat_duration = Duration(1, 4)
            self.beat_duration = beat_duration
        else:
            raise Exception('Illegal argument type {0)', type(tempo_or_function))
        
    def tempo(self, offset, duration):
        """
        Compute a tempo (bpm) setting based on a given offset on domain defined by duration
        The offset is rescaled to the actual range of the function.
        
        Args:
          offset: (Offset) within duration
          duration: (Duration) of domain
        Returns:
          bpm value based on tempo information provided by self.fctn
        """
        # scale to functions domain
        q = (offset.offset/duration.duration) * (convert_to_numeric(self.fctn.domain_end) -
                                                 convert_to_numeric(self.fctn.domain_start))
        return self.fctn.eval(convert_to_numeric(self.fctn.domain_start) + q)

    def __str__(self):
        return '[TempoFctn({0}) per {1} note]'.format(self.fctn, self.beat_duration)

# ==============================================================================
class TempoFunctionEvent(Event):
    """
    An event subclass (type) that defines the event in terms of a dynamics function.  
    """

    def __init__(self, tempo_function, time, beat_duration=None):
        """
        Constructor.
        
        Args:
            tempo_function: TempoFunction behind this event.
            beat_duration: Duration for the beat.
        """
        if not isinstance(tempo_function, UnivariateFunction) and not isinstance(tempo_function, Tempo):
            raise Exception('Input parameter must be UnivariateFunction or Tempo, not {0}'.format(type(tempo_function)))
        objct = TempoFunction(tempo_function, beat_duration)
        self.__beat_duration = beat_duration
        Event.__init__(self, objct, time)
        
    def tempo(self, position, next_event_position):
        """
        Compute the tempo at a given position (re: TempoEventSequence)
        
        Args:
          position: The absolute position (Position) to evaluate at
          next_event_position:  The position (Position) of the starting of the next event.  Can be None is none exists.
        Returns:
          tempo numeric as bpm based on tempo beat
        """
        return self.object.tempo(Offset(position.position - self.time.position),
                                 next_event_position - self.time if next_event_position else Duration(1))
        
    def beat_duration(self):
        return self.__beat_duration

# ==============================================================================
class TempoEventSequence(EventSequence):
    """
    An event sequence specialized to tempo events.
    """

    def __init__(self, event_list=None):
        """
        Constructor.

        Args:
            event_list: TempoEvents to initialize the sequence.
        """
        EventSequence.__init__(self, event_list)
        
    def tempo(self, position):
        tfe = self.floor_event(position)
        if isinstance(tfe, TempoFunctionEvent):
            next_tfe = self.successor(tfe)
            return tfe.tempo(position, next_tfe.time if next_tfe is not None else None)
        else:
            return tfe.tempo()

# ==============================================================================
class Score(object):
    """
    Class representing a score, consisting of a number of instrument voices. It also retains event
         sequences for tempo and time, which are global over all the voices.
    """

    def __init__(self):
        """
        Constructor.
        """
        
        self.__instrument_voices = list()
        # map from instrument class to the instrument voices added.
        self.class_map = dict()
        # map instrument class name to InstrumentClass
        self.name_class_map = dict()
        # HCT not utilized, TODO
        #self.__hct = HarmonicContextTrack()
        
        self.__tempo_sequence = TempoEventSequence()
        self.__time_signature_sequence = TimeSignatureEventSequence()
        
    @property
    def tempo_sequence(self):
        return self.__tempo_sequence
    
    @property
    def time_signature_sequence(self):
        return self.__time_signature_sequence

    @property
    def hct(self):
        return self.__hct
        
    def add_instrument_voice(self, instrument_voice):
        if not isinstance(instrument_voice, InstrumentVoice):
            raise Exception('parameter must be InstrumentVoice type not {0}'.format(type(instrument_voice)))
        instrument_family = instrument_voice.instrument.parent
        instrument_class = instrument_family.parent
        
        # add the name to class map if not already there.
        if instrument_class.name.upper() not in self.name_class_map:
            self.name_class_map[instrument_class.name.upper()] = instrument_class
        
        # Add the map key to class_map if not there,
        #    then append the given instrument voice to to map target.
        if instrument_class not in self.class_map:
            self.class_map[instrument_class] = []
        self.class_map[instrument_class].append(instrument_voice)
        
        # Add the instrument voice to the general list.
        self.__instrument_voices.append(instrument_voice)
            
    def get_class_instrument_voices(self, class_name):
        if class_name.upper() not in self.name_class_map:
            return []
        else:
            return list(self.class_map[class_name.upper()])
    
    @property    
    def instrument_voices(self):
        return list(self.__instrument_voices)
    
    @property
    def instrument_classes(self):
        return [k for (k, _) in self.class_map.items()]

    def get_instrument_voice(self, instrument_name):
        answer = []
        for inst_voice in self.__instrument_voices:
            if inst_voice.instrument.name.upper() == instrument_name.upper():
                answer.append(inst_voice)
        return answer
    
    def remove_instrument_voice(self, instrument_voice):
        if instrument_voice not in self.__instrument_voices:
            raise Exception('Attempt to remove voice {0} which does not exist'.format(
                instrument_voice.instrument.name))
        self.__instrument_voices.remove(instrument_voice)
        
        class_name = instrument_voice.instrument.parent.parent.name
        class_object = self.name_class_map[class_name.upper()]
        class_list = self.class_map[class_object]
        class_list.remove(instrument_voice)
        if len(class_list) == 0:
            self.name_class_map.pop(class_name.upper())
            self.class_map.pop(class_object)
        
    def remove_instrument_class(self, class_name):
        if class_name.upper() not in self.name_class_map:
            raise Exception('Attempt to remove class voices {0} which do not exist'.format(class_name))
        
    @property
    def duration(self):
        return self.length()
    
    def length(self):
        duration = Duration(0)
        for voice in self.__instrument_voices:
            duration = voice.duration if voice.duration > duration else duration
        return duration
    
    def real_time_duration(self):
        interval = Interval(0, self.duration)
        conversion = TimeConversion(self.tempo_sequence, self.time_signature_sequence, Position(self.duration.duration))
        return conversion.position_to_actual_time(interval.upper) 
        
    def get_notes_by_wnt_interval(self, interval):
        """
        Get all the notes in the score by interval:  Return dict structure as follows:
            instrument_voice --> {voice_index --> [notes]}
        """
        answer = {}
        for instrument_voice in self.__instrument_voices:
            answer[instrument_voice] = instrument_voice.get_notes_by_interval(interval)
        return answer
    
    def get_notes_by_rt_interval(self, interval):
        conversion = TimeConversion(self.tempo_sequence, self.time_signature_sequence, Position(self.duration.duration))
        wnt_interval = Interval(conversion.actual_time_to_position(interval.lower),
                                conversion.actual_time_to_position(interval.upper))
        return self.get_notes_by_wnt_interval(wnt_interval)
    
    def get_notes_by_bp_interval(self, interval):
        conversion = TimeConversion(self.tempo_sequence, self.time_signature_sequence, Position(self.duration.duration))
        wnt_interval = Interval(conversion.bp_to_position(interval.lower), conversion.bp_to_position(interval.upper))
        return self.get_notes_by_wnt_interval(wnt_interval)
    
    def get_notes_starting_in_wnt_interval(self, interval):
        """
        Get all the notes starting in the score by whole note time interval:  Return dict structure as follows:
            instrument_voice --> {voice_index --> [notes]}
        """
        answer = {}
        for instrument_voice in self.__instrument_voices:
            answer[instrument_voice] = instrument_voice.get_notes_starting_in_interval(interval)
        return answer
    
    def get_notes_starting_in_rt_interval(self, interval):
        """
        Get all notes starting in the score by an interval based on real time:  Return dict structure as follows:
            instrument_voice --> {voice_index --> [notes]}
        """
        conversion = TimeConversion(self.tempo_sequence, self.time_signature_sequence, Position(self.duration.duration))
        wnt_interval = Interval(conversion.actual_time_to_position(interval.lower),
                                conversion.actual_time_to_position(interval.upper))
        return self.get_notes_starting_in_wnt_interval(wnt_interval)
    
    def get_notes_starting_in_bp_interval(self, interval):
        """
        Get all notes starting in the score by an interval based on beat position:  Return dict structure as follows:
            instrument_voice --> {voice_index --> [notes]}
        """
        conversion = TimeConversion(self.tempo_sequence, self.time_signature_sequence, Position(self.duration.duration))
        wnt_interval = Interval(conversion.bp_to_position(interval.lower), conversion.bp_to_position(interval.upper))
        return self.get_notes_starting_in_wnt_interval(wnt_interval)
    
    @property 
    def beat_duration(self):
        duration = self.duration
        conversion = TimeConversion(self.tempo_sequence, self.time_signature_sequence, Position(self.duration.duration))
        return conversion.position_to_bp(Position(duration.duration))
    
    @property 
    def real_duration(self):
        duration = self.duration
        conversion = TimeConversion(self.tempo_sequence, self.time_signature_sequence, Position(self.duration.duration))
        return conversion.position_to_actual_time(Position(duration.duration))

# ==============================================================================
class ScoreToMidiConverter(object):
    """
    This class is used to convert a score to a midi file.  The procedure is:
    1) Create a converter:  smc = ScoreToMidiConverter(score)
    2) Create the output file:  smc.create(filename)
    
    Note:
      All tempos messages are on channel 1 track 0
      All note messages are on channel 1 for other tracks.
    """
    
    # Number of MIDI ticks per quarter note.
    TICKS_PER_BEAT = 480
    DEFAULT_NOTE_CHANNEL = 1
    DEFAULT_VELOCITY = 64
    # number of ms between volume events for dynamic function events
    VOLUME_EVENT_DURATION_MS = 5
    TEMPO_EVENT_DURATION_MS = 50
    
    DEFAUTLT_BEAT_DURATION = Duration(1, 4)

    def __init__(self, score):
        """
        Constructor.  Set up the tick track map.
        
        Args:
          score:  of Score class 
        """
        
        self.__score = score
        self.__filename = ''
        self.__trace = False
        self.mid = None
        self.inst_voice_channel = {}
        self.channel_assignment = 1
        self.fine_tempo_sequence = None
        self.time_conversion = None
        
    def create(self, filename, trace=False):
        """
        Create a midi file from the score, with midi filename provided.
        
        Args:
          filename - String filename.  Can include path, should have filetype '.mid'.
        """
        self.__filename = filename
        self.__trace = trace
        
        self.mid = MidiFile(type=1)
        
        self.mid.ticks_per_beat = ScoreToMidiConverter.TICKS_PER_BEAT
        
        # assign each instrument voice to a channel
        self.inst_voice_channel = {}
        
        # used for assigning channels to each voice.
        self.channel_assignment = 1
                       
        (self.fine_tempo_sequence, self.time_conversion) = self._build_time_conversion()
                   
        meta_track = MidiTrack()
        self.mid.tracks.append(meta_track)
        self._fill_meta_track(meta_track)
        
        self._assign_voices_tracks()
        
        self.mid.save(self.filename)
        
    @property
    def score(self):
        return self.__score
    
    @property
    def filename(self):
        return self.__filename
    
    @staticmethod
    def convert_score(score, filename):
        """
        Static method to convert a Score to a midi file.
        
        Args:
          score: Class Score object
          filename: The name of the midi file, should have filetype .mid
        """
        smc = ScoreToMidiConverter(score)
        smc.create(filename)
        
    @staticmethod 
    def convert_line(line, filename, tempo=Tempo(60, Duration(1, 4)),
                     time_signature=TimeSignature(4, Duration(1, 4)), instrument_name='piano'):
        """
        Static method to convert a Line to a midi file
        
        Args:
          line: Class Line object
          filename: The name of the midi file, should have filetype .mid
          tempo: Tempo for playback, default is 60 BPM tempo beat = quarter note
          time_signature: TimeSiganture on playback, default is 4 quarter notes
          instrument_name: Name of instrument ot use for playback.
        """
        score = Score()
        tempo_sequence = score.tempo_sequence
        tempo_sequence.add(TempoEvent(tempo, Position(0)))
                
        ts_sequence = score.time_signature_sequence
        ts_sequence.add(TimeSignatureEvent(time_signature, Position(0)))
        
        c = InstrumentCatalog.instance() 
        instrument = c.get_instrument(instrument_name)
        if instrument is None:
            print('Error: instrument {0} cannnot be found'.format(instrument_name))
            return

        instrument_voice = InstrumentVoice(instrument, 1)
        piano_voice = instrument_voice.voice(0)
        
        piano_voice.pin(line, Offset(0))
              
        score.add_instrument_voice(instrument_voice)
        ScoreToMidiConverter.convert_score(score, filename)
    
    def _assign_voices_tracks(self):
        # assign a channel to each instrument voice
        for inst_voice in self.score.instrument_voices:
            self.inst_voice_channel[inst_voice] = self._next_channel()
            self._add_notes(inst_voice, self.inst_voice_channel[inst_voice])
            
    def _next_channel(self):
        """
        Allocates channels starting at 1 through 15. Raises exception beyond that.
        """
        if self.channel_assignment == 15:
            raise Exception('Ran out of channels.')
        self.channel_assignment += 1
        if self.channel_assignment == 9:  # drums
            return self._next_channel()
        return self.channel_assignment
            
    def _add_notes(self, inst_voice, channel):
        voice_note_map = inst_voice.get_all_notes()
        
        for voice, notes in voice_note_map.items():
            track = MidiTrack()
            track.name = inst_voice.instrument.name
            self.mid.tracks.append(track)
            # For each note
            #    build a note on and off message, compute the ticks of the message
            #    append both messages to out list msgs
            velocity_msgs = self._gen_velocity_msgs(voice, channel)
            msgs = [] 
            for n in notes:
                # We do not need to set velocity outside of the default 
                # Crescendo and decrescendo are taken care of by channel change messages only,
                #       which modify the constant velocity set per note.
                # If the velocity was set here, the channel  change would distort the setting.
                # Otherwise, the velocity would be acquired as follows
                ticks = self._wnt_to_ticks(n.get_absolute_position())
                msg = NoteMessage('note_on', channel, n.diatonic_pitch.chromatic_distance + 12, ticks,
                                  ScoreToMidiConverter.DEFAULT_VELOCITY)
                msgs.append(msg)
                end_ticks = self._wnt_to_ticks(n.get_absolute_position() + n.duration)
                msg = NoteMessage('note_off', channel, n.diatonic_pitch.chromatic_distance + 12, end_ticks)
                msgs.append(msg)
        
            # Sort the msgs list by tick time, and respect to off before on if same time
            msgs.extend(velocity_msgs)

            from functools import cmp_to_key
            msgs = sorted(msgs, key=cmp_to_key(lambda x, y: ScoreToMidiConverter.compare_note_msgs(x, y)))
    
            prior_tick = 0
            for m in msgs:
                logging.info('{0}'.format(m))
                ticks_value = int(m.abs_tick_time - prior_tick)
                # Append the midi message to the track, with tics being incremental over succeeding messages.
                # We default to channel 1 for all tracks.
                track.append(m.to_midi_message(ticks_value))
                prior_tick = m.abs_tick_time
                if self.__trace:
                    print('{0}/{1}'.format(ticks_value, m))
            
    def _gen_velocity_msgs(self, voice, channel):
        """
        The method runs through the dynamic sequence events, and generates channel change events to set velocity.
        In the case of a DynamicsEvent, the process is trivial.
        In the case of a DynamicsFunctionEvent, we generate channel change events in small steps over the domain
        of the event, providing a 'simulation' of velocity changes as dictated by the function behind the event.
        """
        msgs = []
        dyn_seq = voice.dynamics_sequence.sequence_list
        voice_len = voice.length()
        
        tc = self.time_conversion 
        
        for event in dyn_seq:
            if event.time >= voice_len:
                break
            if isinstance(event, DynamicsEvent):
                velocity = event.velocity()
                ticks = self._wnt_to_ticks(event.time)
                msgs.append(ExpressionVelocityMessage(channel, ticks, velocity))
            elif isinstance(event, DynamicsFunctionEvent):
                t1 = tc.position_to_actual_time(event.time)
                next_event = voice.dynamics_sequence.successor(event)
                t2 = tc.position_to_actual_time(next_event if next_event is not None else Position(voice_len.duration))
                while t1 < t2:
                    wnt = tc.actual_time_to_position(t1)
                    ticks = self._wnt_to_ticks(wnt)
                    velocity = int(event.velocity(wnt, next_event.time if next_event is not None else
                                   Position(voice_len.duration)))
                    msgs.append(ExpressionVelocityMessage(channel, ticks, velocity))
                    t1 += ScoreToMidiConverter.VOLUME_EVENT_DURATION_MS
                   
        return msgs
            
    def _fill_meta_track(self, meta_track):            
        event_list = self.score.tempo_sequence.sequence_list
        score_len = self.score.length()
        
        #  Loop over list, for every change in tempo , the tempo should be reset.
        #  Note, that there may be tempo or ts changes that last for 0 duration - we skip those.
        last_tick_time = 0
        for tempo_event in event_list:
            if tempo_event.time >= score_len:
                break
            if isinstance(tempo_event, TempoEvent):
                current_tick_time = self._wnt_to_ticks(tempo_event.time)
            
                # If there is a ts and tempo event, effect a midi tempo change
                beat_ratio = Fraction(1, 4) / tempo_event.object.beat_duration.duration
                
                # tempo_value = (60/BPM) * (ts_beat / tempo_beat)
                tempo_value = int((60.0 / tempo_event.object.tempo) * beat_ratio * 1000000)
                
                ticks = int(current_tick_time - last_tick_time)
                msg = MetaMessage('set_tempo', tempo=tempo_value, time=ticks)
                meta_track.append(msg)   
                last_tick_time = current_tick_time
            elif isinstance(tempo_event, TempoFunctionEvent):
                #  Run over event range making a small step function effectively, and setting the tempo
                #  every TEMPO_EVENT_DURATION_MS.
                t1 = tempo_event.time
                beat_duration = tempo_event.beat_duration if tempo_event.beat_duration is None else \
                    ScoreToMidiConverter.DEFAUTLT_BEAT_DURATION
                next_event = self.score.tempo_sequence.successor(tempo_event)
                t2 = next_event.time if next_event is not None else Position(score_len.duration)
                while t1 < t2:
                    tempo = int(tempo_event.tempo(t1, next_event.time if next_event is not None else
                                Position(score_len)))
                    delta_wnt = (tempo * ScoreToMidiConverter.TEMPO_EVENT_DURATION_MS * beat_duration.duration) / \
                                (60.0 * 1000.0)
                    
                    current_tick_time = self._wnt_to_ticks(t1)
                    ticks = int(current_tick_time - last_tick_time)
                    
                    # If there is a ts and tempo event, effect a midi tempo change
                    beat_ratio = Fraction(1, 4) / beat_duration.duration
                
                    # tempo_value = (60/BMP) * (ts_beat / tempo_beat)
                    tempo_value = int((60.0 / tempo) * beat_ratio * 1000000)
                    msg = MetaMessage('set_tempo', tempo=tempo_value, time=ticks)
                    meta_track.append(msg)                      
                    
                    t1 += delta_wnt
                    last_tick_time = current_tick_time
     
    def _build_time_conversion(self):
        event_list = self.score.tempo_sequence.sequence_list
        score_len = self.score.length()
        
        fine_tempo_sequence = TempoEventSequence()
        
        for event in event_list:
            if isinstance(event, TempoEvent):
                fine_tempo_sequence.add(TempoEvent(event.object, event.time))
            elif isinstance(event, TempoFunctionEvent):
                t1 = event.time
                beat_duration = event.beat_duration if event.beat_duration is None else \
                    ScoreToMidiConverter.DEFAUTLT_BEAT_DURATION
                next_event = self.score.tempo_sequence.successor(event)
                t2 = next_event.time if next_event is not None else Position(score_len.duration)
                while t1 < t2:
                    tempo = int(event.tempo(t1, next_event.time if next_event is not None else Position(score_len)))
                    delta_wnt = (tempo * ScoreToMidiConverter.TEMPO_EVENT_DURATION_MS * beat_duration.duration) / \
                                (60.0 * 1000.0)
                    
                    fine_tempo_sequence.add(TempoEvent(Tempo(tempo, beat_duration), t1))  

                    t1 += delta_wnt

        tc = TimeConversion(fine_tempo_sequence, self.score.time_signature_sequence, Position(score_len))  
        
        return fine_tempo_sequence, tc
                
    def _wnt_to_ticks(self, wnt):
        # Convert whole note time to ticks.
        offset = convert_to_numeric(wnt)
        return int((offset / Fraction(1, 4)) * self.mid.ticks_per_beat)
    
    @staticmethod
    def compare_note_msgs(a, b):
        a_ticks = a.abs_tick_time
        b_ticks = b.abs_tick_time
        comp_value = -1 if a_ticks < b_ticks else 1 if a_ticks > b_ticks else 0
        if isinstance(a, ExpressionVelocityMessage) or isinstance(b, ExpressionVelocityMessage):
            return comp_value
        
        if comp_value != 0:
            return comp_value
        a_is_note_off = a.msg_type == 'note_off'
        b_is_note_off = b.msg_type == 'note_off'
        if a_is_note_off and not b_is_note_off:
            return -1
        if not a_is_note_off and b_is_note_off:
            return 1
        return 0
       

class MidiMessage(object):
    
    def __init__(self, msg_type, channel, abs_tick_time):
        self.__msg_type = msg_type
        self.__channel = channel
        self.__abs_tick_time = abs_tick_time
        
    @property
    def msg_type(self):
        return self.__msg_type
    
    @property
    def channel(self):
        return self.__channel
    
    @property
    def abs_tick_time(self):
        return self.__abs_tick_time 
    
    def to_midi_message(self, prior_msg_ticks):
        return None   


class NoteMessage(MidiMessage):
    
    def __init__(self, msg_type, channel, note_value, abs_tick_time, velocity=Dynamics.DEFAULT_DYNAMICS_VELOCITY()):
        MidiMessage.__init__(self, msg_type, channel, abs_tick_time)
        self.__note_value = note_value
        self.__velocity = velocity
        
    @property
    def note_value(self):
        return self.__note_value
  
    @property
    def velocity(self):
        return self.__velocity
    
    def to_midi_message(self, ticks_from_prior_msg):
        return Message(self.msg_type, note=self.note_value, velocity=self.velocity, time=ticks_from_prior_msg,
                       channel=self.channel)
    
    def __str__(self):
        return '{0} {1}[{2}]:pv=({3}, {4})'.format(self.abs_tick_time, self.msg_type, self.channel, self.note_value,
                                                   self.velocity)


class ExpressionVelocityMessage(MidiMessage):
    
    def __init__(self, channel, abs_tick_time, velocity=Dynamics.DEFAULT_DYNAMICS_VELOCITY()):
        MidiMessage.__init__(self, 'control_change', channel, abs_tick_time)
        self.__velocity = velocity
    
    @property
    def velocity(self):
        return self.__velocity
    
    def to_midi_message(self, ticks_from_prior_msg):
        return Message(self.msg_type, control=11, value=self.velocity, time=ticks_from_prior_msg,
                       channel=self.channel)
    
    def __str__(self):
        return '{0} {1}/{2}({3})'.format(self.abs_tick_time, self.msg_type, self.channel, self.velocity)
    
# ==============================================================================
# ============================================================================== 13
# ==============================================================================

class StepwiseFunction(UnivariateFunction):
    """
    Stepwise function, steps defined by a set of transition points
    
    For example, (5, 1), (7, 3), (10, 6), (12, 8)  has the following linear segments:
    (5, 1) to (7, 3)
    (7, 3) to (10, 6)
    (10, 6) to 12, 8)
             
    if restrict_domain is specified (True), evaluation points must be within domain bounds.
    """

    def __init__(self, transition_points=None, restrict_domain=False):
        """
        Constructor.
        
        Args:
        transition_points: non-empty list of ordered pairs (x, y)
        restrict_domain: boolean indicating if evaluation points must be in defined domain of transition points.
                         default is False.
        """
        if transition_points is None:
            transition_points = list()
        if transition_points is None or not isinstance(transition_points, list):
            assert Exception('Illegal argument to SetwiseLinearFunction {0}'.format(transition_points))
        self.__restrict_domain = restrict_domain
        self._setup(transition_points)
        
    def _setup(self, transition_points):
        self.__transition_points = sorted(transition_points, key=lambda x: x[0])
        self.__domain_start = self.__transition_points[0][0]
        self.__domain_end = self.__transition_points[len(self.__transition_points) - 1][0]
        
        self.ordered_map = OrderedMap(self.transition_points)
        
    @property
    def transition_points(self):
        return self.__transition_points
    
    @property
    def domain_start(self):
        return self.__domain_start
    
    @property
    def domain_end(self):
        return self.__domain_end
    
    @property 
    def restrict_domain(self):
        return self.__restrict_domain
        
    def eval(self, x):
        if len(self.transition_points) == 0:
            raise Exception("The function is undefined due to lack of transition points.")
        if self.restrict_domain:
            if x < self.domain_start or x > self.domain_end:
                raise Exception('Input {0} out of range [{1}, {2}]'.format(x, self.domain_start, self.domain_end))
        key = self.ordered_map.floor(x)
        if key is None:
            return self.ordered_map.get(self.domain_start)
        if key == self.domain_end:
            return self.ordered_map.get(self.domain_end)
        else:
            return self.ordered_map.get(key)
        
    def add(self, transition_point):
        """
        Add a transition point to the stepwise function.
        
        Args:
          transition_point: Pair (x, y)  x, y are numerics.
        """
        new_points = list(self.transition_points)
        new_points.append(transition_point)
        self._setup(new_points)
        
    def add_and_clear_forward(self, transition_point):
        """
        Add a transition point to the stepwise function AND clear out higher (domain value) transition points.
        
        Args:
          transition_point: Pair (x, y)  x, y are numerics.
        """
        new_points = []
        elimination_value = transition_point[0]
    
        for p in self.transition_points:
            if p[0] < elimination_value:
                new_points.append(p) 
        new_points.append(transition_point)
    
        self._setup(new_points)

# ==============================================================================
class LinearSegment(object):
    """
    This class defines a linear segment based on two tuples of coordinates.
    """
    def __init__(self, start_coords, end_coords):
        """
        A linear segement between two sets of coordinates.
        :param start_coords: (x, y) of the first coordinate.
        :param end_coords: (x, y) of the second coordinte.
        """
        self.domain_start = start_coords[0]
        self.domain_end = end_coords[0]

        self.xcoef = (end_coords[1] -
                      start_coords[1])/float((convert_to_numeric(self.domain_end) -
                                              convert_to_numeric(self.domain_start)))
        self.ycoef = start_coords[1] - self.xcoef * convert_to_numeric(self.domain_start)
        
    def eval(self, value):
        return self.xcoef * value + self.ycoef


class PiecewiseLinearFunction(UnivariateFunction):
    """
    Piecewise linear function, steps defined by a set of transition points, where values between the ordinates
    of adjacent transitions points, are based on a linear interpolation of the transition points' values.
    
    For example, (3, 5), (7, 10), (10, 14), (12, 2)  has the following steps:
       (-3, 5
       (3-7, 5),
       (7-10, 10),
       (10-12, 14),
       (12-, 2)
       
       if restrict_domain is specified (True), evaluation points must be within domain bounds.
    """

    def __init__(self, transition_points=list(), restrict_domain=False):
        """
        Constructor.
        
        Args:
        transition_points: non-empty list of ordered pairs (x, y), x is the domain, y the range.
        restrict_domain: boolean indicating if evaluation points must be in defined domain of transition points.
                         default is False.
        """
        if transition_points is None or not isinstance(transition_points, list):
            assert Exception('Illegal argument to SetwiseLinearFunction {0}'.format(transition_points))
        self.__restrict_domain = restrict_domain
        self._setup(transition_points)
        
    def _setup(self, transition_points):
        self.__transition_points = sorted(transition_points, key=lambda x: x[0])
        self.__domain_start = self.__transition_points[0][0]
        self.__domain_end = self.__transition_points[len(self.__transition_points) - 1][0]
        
        lin_segs = []
        for i in range(0, len(self.transition_points) - 1):
            lin_segs.append((self.transition_points[i][0],
                             LinearSegment(self.transition_points[i], self.transition_points[i + 1])))
        
        self.ordered_map = OrderedMap(lin_segs)
        
    @property
    def transition_points(self):
        return self.__transition_points
    
    @property
    def restrict_domain(self):
        return self.__restrict_domain
    
    @property
    def domain_start(self):
        return self.__domain_start
    
    @property
    def domain_end(self):
        return self.__domain_end

    def __call__(self, x):
        return self.eval(x)
        
    def eval(self, x):
        if len(self.transition_points) == 0:
            raise Exception("The function is undefined due to lack of transition points.")
        if self.restrict_domain:
            if x < self.domain_start or x > self.domain_end:
                raise Exception('Input {0} out of range [{1}, {2}]'.format(x, self.domain_start, self.domain_end))

        if x <= self.domain_start:
            return self.transition_points[0][1]
        if x >= self.domain_end:
            return self.transition_points[len(self.transition_points) - 1][1]
        key = self.ordered_map.floor(x)
        lin_seg = self.ordered_map.get(key)
        return lin_seg.eval(x)
    
    def add(self, transition_point):
        """
        Add a transition point to the piecewise function.
        
        Args:
          transition_point: Pair (x, y)  x, y are numerics.
        """
        new_points = list(self.transition_points)
        new_points.append(transition_point)
        self._setup(new_points)
        
    def add_and_clear_forward(self, transition_point):
        """
        Add a transition point to the piecewise function AND clear out higher (domain value) transition points.
        
        Args:
          transition_point: Pair (x, y)  x, y are numerics.
        """
        new_points = []
        elimination_value = transition_point[0]
    
        for p in self.transition_points:
            if p[0] < elimination_value:
                new_points.append(p) 
        new_points.append(transition_point)
    
        self._setup(new_points)

# ==============================================================================
class GenericUnivariateFunction(UnivariateFunction):
    """
    A generalization of UnivariateFunction that allows a user define function to be used.
    This is a wrapper for functions that are univariate but not necessarily a subclass of UnivariateFunction.
    """
    
    def __init__(self, f, domain_start, domain_end, restrict_domain=False):
        """
        Constructor.
        
        Args:
        f: User-defined univariate function, but not necessarily a subclass of UnivariateFunction.
        domain_start: numeric-like that defines the start of a domain (first point)
        domain_end: numeric_like tat defines the end of a domain (last point)
        restrict_domain: boolean meaning to throw exception for evaluations outside the domain
        """
        self.__domain_start = domain_start
        self.__domain_end = domain_end
        
        self.__f = f
        
        self.__restrict_domain = restrict_domain
        
    @property
    def domain_start(self):
        return self.__domain_start
    
    @property
    def domain_end(self):
        return self.__domain_end
    
    @property
    def restrict_domain(self):
        return self.__restrict_domain
    
    @property
    def f(self):
        return self.__f
    
    def eval(self, x):
        if self.restrict_domain:
            if x < self.domain_start or x > self.domain_end:
                raise Exception('{0} must be in [{1}, {2}]'.format(x, self.domain_start, self.domain_end))
        return self.f(x)



# ==============================================================================