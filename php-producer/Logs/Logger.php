<?php

class Logger
{
    private string $filePath;

    public function __construct(string $fileName)
    {
        $this->filePath = __DIR__ . '/Log_Files/' . $fileName;

        $dir = dirname($this->filePath);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
    }

    public function handle(string $message)
    {
        file_put_contents(
            $this->filePath,
            date('Y-m-d H:i:s') . " " . $message . "\n",
            FILE_APPEND | LOCK_EX
        );
    }
}

?>