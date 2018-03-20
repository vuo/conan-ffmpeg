#include <stdio.h>
extern "C" {
#include <libavcodec/avcodec.h>
}

int main()
{
	printf("Successfully initialized FFmpeg 0x%x.\n", avcodec_version());
	return 0;
}
