class ConfidenceWeight:
    def __init__(
        self,
        author_weight,
        subject_weight,
        description_weight,
        filenames_weight,
        author_date_weight,
    ):
        self.author_weight = author_weight
        self.subject_weight = subject_weight
        self.description_weight = description_weight
        self.filenames_weight = filenames_weight
        self.author_date_weight = author_date_weight

    def __str__(self):
        print(
            "Confidence matrix: "
            + self.author_weight
            + ","
            + self.subject_weight
            + ","
            + self.description_weight
            + ","
            + self.filenames_weight
            + ","
            + self.author_date_weight
        )
