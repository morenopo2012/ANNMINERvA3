# MIT License
# 
# Copyright (c) 2018 Domenick Poster
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import glob
import os
import shutil
import tensorflow as tf

class Checkpoint(object):
    dir = None
    file = None
    score = None
    path = None
    
    def __init__(self, path, score):
        self.dir = os.path.dirname(path)
        self.file = os.path.basename(path)
        self.score = score
        self.path = path


class BestCheckpointCopier(tf.estimator.Exporter):
    checkpoints = None
    checkpoints_to_keep = None
    compare_fn = None
    name = None
    score_metric = None
    sort_key_fn = None
    sort_reverse = None
    
    def __init__(
        self, name='best_checkpoints', checkpoints_to_keep=5,
        score_metric='Loss/total_loss',
        compare_fn=lambda x,y: x.score < y.score,
        sort_key_fn=lambda x: x.score, sort_reverse=False
    ):
        self.checkpoints = []
        self.checkpoints_to_keep = checkpoints_to_keep
        self.compare_fn = compare_fn
        self.name = name
        self.score_metric = score_metric
        self.sort_key_fn = sort_key_fn
        self.sort_reverse = sort_reverse
        super(BestCheckpointCopier, self).__init__()
    
    def _copyCheckpoint(self, checkpoint):
        desination_dir = self._destinationDir(checkpoint)
        os.makedirs(desination_dir, exist_ok=True)
    
        for file in glob.glob(r'{}*'.format(checkpoint.path)):
            self._log('copying {} to {}'.format(file, desination_dir))
            shutil.copy(file, desination_dir)
    
    def _destinationDir(self, checkpoint):
        return os.path.join(checkpoint.dir, self.name)
    
    def _keepCheckpoint(self, checkpoint):
        self._log('keeping checkpoint {} with score {}'.format(checkpoint.file,
            checkpoint.score))
        
        self.checkpoints.append(checkpoint)
        self.checkpoints = sorted(self.checkpoints, key=self.sort_key_fn,
            reverse=self.sort_reverse)
        
        self._copyCheckpoint(checkpoint)
    
    def _log(self, statement):
        tf.logging.info('[{}] {}'.format(self.__class__.__name__, statement))
    
    def _pruneCheckpoints(self, checkpoint):
        destination_dir = self._destinationDir(checkpoint)
        
        for checkpoint in self.checkpoints[self.checkpoints_to_keep:]:
          self._log('removing old checkpoint {} with score {}'.format(
            checkpoint.file, checkpoint.score))
        
          old_checkpoint_path = os.path.join(destination_dir, checkpoint.file)
          for file in glob.glob(r'{}*'.format(old_checkpoint_path)):
            self._log('removing old checkpoint file {}'.format(file))
            os.remove(file)
        
        self.checkpoints = self.checkpoints[0:self.checkpoints_to_keep]
    
    def _score(self, eval_result):
        return float(eval_result[self.score_metric])

    def _shouldKeep(self, checkpoint):
        return (len(self.checkpoints) < self.checkpoints_to_keep or
            self.compare_fn(checkpoint, self.checkpoints[-1]))
    
    def export(self, estimator, export_path, checkpoint_path, eval_result,
        is_the_final_export):
        self._log('export checkpoint {}'.format(checkpoint_path))
        
        score = self._score(eval_result)
        checkpoint = Checkpoint(path=checkpoint_path, score=score)
        
        if self._shouldKeep(checkpoint):
            self._keepCheckpoint(checkpoint)
            self._pruneCheckpoints(checkpoint)
        else:
            self._log('skipping checkpoint {}'.format(checkpoint.path))
