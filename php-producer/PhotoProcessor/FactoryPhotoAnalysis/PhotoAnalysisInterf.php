<?php

    interface PhotoAnalysisInterf{
        public function getAnalysis();
        public function getRecommendations();
        public function getHealthRating();

        public function getFullResult() : array;
    }

?>