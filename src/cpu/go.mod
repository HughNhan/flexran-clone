module github.com/jianzzha/cpuinfo

go 1.16

require (
	github.com/antchfx/xmlquery v1.3.6
	github.com/google/cadvisor v0.39.0
	k8s.io/klog/v2 v2.4.0
)

replace github.com/antchfx/xmlquery => ./antchfx/xmlquery
