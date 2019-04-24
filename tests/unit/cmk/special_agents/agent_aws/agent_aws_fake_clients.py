#!/usr/bin/env python

import abc
import random

#   .--entities------------------------------------------------------------.
#   |                             _   _ _   _                              |
#   |                   ___ _ __ | |_(_) |_(_) ___  ___                    |
#   |                  / _ \ '_ \| __| | __| |/ _ \/ __|                   |
#   |                 |  __/ | | | |_| | |_| |  __/\__ \                   |
#   |                  \___|_| |_|\__|_|\__|_|\___||___/                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   ---abc------------------------------------------------------------------


class Entity(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, key):
        self.key = key

    @abc.abstractmethod
    def create(self, idx, amount):
        return


#   ---structural-----------------------------------------------------------


class List(Entity):
    def __init__(self, key, *elements):
        super(List, self).__init__(key)
        self._elements = elements

    def create(self, idx, amount):
        return [{e.key: e.create("%s-%s" % (idx, x), amount)
                 for e in self._elements}
                for x in xrange(amount)]


class Dict(Entity):
    def __init__(self, key, *values):
        super(Dict, self).__init__(key)
        self._values = values

    def create(self, idx, amount):
        return {v.key: v.create(idx, amount) for v in self._values}


#   ---behavioural----------------------------------------------------------


class Str(Entity):
    def create(self, idx, amount):
        return "%s-%s" % (self.key, idx)


class Int(Entity):
    def create(self, idx, amount):
        return random.choice(xrange(100))


class Float(Entity):
    def create(self, idx, amount):
        return 1.0 * random.choice(xrange(100))


class Timestamp(Entity):
    def create(self, idx, amount):
        return "2019-%02d-%02d" % (
            random.choice(xrange(1, 13)),
            random.choice(xrange(1, 29)),
        )


class Enum(Entity):
    def create(self, idx, amount):
        return ['%s-%s-%s' % (self.key, idx, x) for x in xrange(amount)]


class Choice(Entity):
    def __init__(self, key, choices):
        super(Choice, self).__init__(key)
        self._choices = choices

    def create(self, idx, amount):
        return random.choice(self._choices)


class BoolChoice(Choice):
    def __init__(self, key):
        super(BoolChoice, self).__init__(key, [True, False])


#.
#   .--creators------------------------------------------------------------.
#   |                                    _                                 |
#   |                 ___ _ __ ___  __ _| |_ ___  _ __ ___                 |
#   |                / __| '__/ _ \/ _` | __/ _ \| '__/ __|                |
#   |               | (__| | |  __/ (_| | || (_) | |  \__ \                |
#   |                \___|_|  \___|\__,_|\__\___/|_|  |___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   .--abc------------------------------------------------------------------


class InstanceCreator(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, idx, amount):
        self._idx = idx
        self._amount = amount
        self._inst = {}

    def add(self, value):
        self._inst[value.key] = value.create(self._idx, self._amount)

    def create(self):
        self._fill_instance()
        return self._inst

    def _fill_instance(self):
        pass

    @classmethod
    def create_instances(cls, amount):
        return [cls(idx, amount).create() for idx in xrange(amount)]


#.
#   .--S3-------------------------------------------------------------------


class S3ListBucketsInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('Name'))
        self.add(Timestamp('CreationDate'))


class S3BucketTaggingInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('Key'))
        self.add(Str('Value'))


#.
#   .--Cloudwatch-----------------------------------------------------------


class CloudwatchDescribeAlarmsInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('AlarmName'))
        self.add(Str('AlarmArn'))
        self.add(Str('AlarmDescription'))
        self.add(Timestamp('AlarmConfigurationUpdatedTimestamp'))
        self.add(BoolChoice('ActionsEnabled'))
        self.add(Enum('OKActions'))
        self.add(Enum('AlarmActions'))
        self.add(Enum('InsufficientDataActions'))
        self.add(Choice('StateValue', ['OK', 'ALARM', 'INSUFFICIENT_DATA']))
        self.add(Str('StateReason'))
        self.add(Str('StateReasonData'))
        self.add(Timestamp('StateUpdatedTimestamp'))
        self.add(Str('MetricName'))
        self.add(Str('Namespace'))
        self.add(Choice('Statistic', [
            'SampleCount',
            'Average',
            'Sum',
            'Minimum',
            'Maximum',
        ]))
        self.add(Str('ExtendedStatistic'))
        self.add(List(
            'Dimensions',
            Str('Name'),
            Str('Value'),
        ))
        self.add(Int('Period'))
        self.add(
            Choice('Unit', [
                'Seconds',
                'Microseconds',
                'Milliseconds',
                'Bytes',
                'Kilobytes',
                'Megabytes',
                'Gigabytes',
                'Terabytes',
                'Bits',
                'Kilobits',
                'Megabits',
                'Gigabits',
                'Terabits',
                'Percent',
                'Count',
                'Bytes/Second',
                'Kilobytes/Second',
                'Megabytes/Second',
                'Gigabytes/Second',
                'Terabytes/Second',
                'Bits/Second',
                'Kilobits/Second',
                'Megabits/Second',
                'Gigabits/Second',
                'Terabits/Second',
                'Count/Second',
                'None',
            ]))
        self.add(Int('EvaluationPeriods'))
        self.add(Int('DatapointsToAlarm'))
        self.add(Float('Threshold'))
        self.add(
            Choice('ComparisonOperator', [
                'GreaterThanOrEqualToThreshold',
                'GreaterThanThreshold',
                'LessThanThreshold',
                'LessThanOrEqualToThreshold',
            ]))
        self.add(Str('TreatMissingData'))
        self.add(Str('EvaluateLowSampleCountPercentile'))
        self.add(
            List(
                'Metrics',
                Str('Id'),
                Dict(
                    'MetricStat',
                    Dict(
                        'Metric',
                        Str('Namespace'),
                        Str('MetricName'),
                        List(
                            'Dimensions',
                            Str('Name'),
                            Str('Value'),
                        ),
                    ), Int('Period'), Str('Stat'),
                    Choice('Unit', [
                        'Seconds',
                        'Microseconds',
                        'Milliseconds',
                        'Bytes',
                        'Kilobytes',
                        'Megabytes',
                        'Gigabytes',
                        'Terabytes',
                        'Bits',
                        'Kilobits',
                        'Megabits',
                        'Gigabits',
                        'Terabits',
                        'Percent',
                        'Count',
                        'Bytes/Second',
                        'Kilobytes/Second',
                        'Megabytes/Second',
                        'Gigabytes/Second',
                        'Terabytes/Second',
                        'Bits/Second',
                        'Kilobits/Second',
                        'Megabits/Second',
                        'Gigabits/Second',
                        'Terabits/Second',
                        'Count/Second',
                        'None',
                    ])),
                Str('Expression'),
                Str('Label'),
                BoolChoice('ReturnData'),
            ))


#.
#   .--CE-------------------------------------------------------------------


class CEGetCostsAndUsageInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Dict(
            'TimePeriod',
            Str('Start'),
            Str('End'),
        ))
        self.add(Dict('Total', Dict(
            'string',
            Str('Amount'),
            Str('Unit'),
        )))
        self.add(
            List(
                'Groups',
                Enum('Keys'),
                Dict('Metrics', Dict(
                    'string',
                    Str('Amount'),
                    Str('Unit'),
                )),
            ))
        self.add(BoolChoice('Estimated'))
