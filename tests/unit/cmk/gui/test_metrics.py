
import cmk.gui.metrics as metrics

def test_registered_renderers():
    registered_plugins = sorted(metrics.renderer_registry.keys())
    assert registered_plugins == [
        'dual',
        'linear',
        'logarithmic',
        'stacked'
    ]
