from DownstreamTracker.DownstreamMatcher import DownstreamMatcher
from Objects.Patch import Patch

a = 'bruh'
p1 = Patch(a,a,a,a,a,a,a,['test2'],"diffffff")
p2 = Patch(a,a,a,a,a,a,a,['test1', 'test2'],"difffff")
matcher = DownstreamMatcher({1:p1})
ans = matcher.get_matching_patch(p2)
print("done")