"""The labelled synthetic action dataset for the risk model (story US-21).

The generator writes sessions between Vera and customers of the demo bank: normal
customer service and the five failure modes in proposal Section 2.1. Every action is
labelled by the rules in data/synthetic/labelling-rules.md, applied in code, and the
sessions are split 70/15/15 into train, validation and test.

The split files are rebuilt from the seed and are not committed. manifest.json is
committed and holds the checksum of each split, so a rebuilt test set is provably
the frozen one. README.md in this folder is the dataset card.

To read a split in code (US-04), after ``py -m data.synthetic.dataset write``:

    from data.synthetic.dataset import read_split
    from data.synthetic.models import DatasetSplit

    train = read_split(DatasetSplit.TRAIN)
"""

from data.synthetic.dataset.files import DatasetMismatch, read_split
from data.synthetic.dataset.generator import GENERATOR_VERSION, SEED, generate

__all__ = ["GENERATOR_VERSION", "SEED", "DatasetMismatch", "generate", "read_split"]
